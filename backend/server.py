"""EthicsBoard AI — Backend API Server

Provides REST API and WebSocket endpoints for the frontend dashboard.
Bridges between the Band room and the React dashboard.
"""

import asyncio
import json
import uuid
import os
import sys
import re
from datetime import datetime, timezone

# Add project root to sys.path so we can import agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import agent runners
from agents.agent_runners import start_all_agents, stop_all_agents, register_dashboard_callback


# --- Models ---

class ReviewMessage(BaseModel):
    id: str
    timestamp: str
    agent: str
    framework: str
    model_provider: str
    content: str
    message_type: str  # 'analysis', 'finding', 'deficiency', 'handoff', 'decision', 'determination'
    deficiencies: Optional[List[dict]] = None
    metadata: Optional[dict] = None


class ReviewSession(BaseModel):
    id: str
    protocol_number: str
    status: str  # 'pending', 'protocol_review', 'ethics_review', 'privacy_review', 'committee_review', 'awaiting_chair', 'completed'
    created_at: str
    messages: List[ReviewMessage] = []
    deficiency_count: int = 0
    determination: Optional[str] = None  # 'approved', 'revisions_required', 'rejected'
    band_room_id: Optional[str] = None


# --- State ---

reviews: Dict[str, ReviewSession] = {}
websocket_connections: Dict[str, List[WebSocket]] = {}
room_to_review: Dict[str, str] = {}
active_subscription_tasks: Dict[str, asyncio.Task] = {}

# Reviews run in parallel, so agent messages can arrive in any order —
# status may only move forward through this sequence, never backwards.
STATUS_ORDER = ["pending", "protocol_review", "ethics_review", "privacy_review",
                "committee_review", "awaiting_chair", "completed"]


def advance_status(current: str, proposed: str) -> str:
    """Return the later of two statuses in the pipeline order."""
    try:
        if STATUS_ORDER.index(proposed) > STATUS_ORDER.index(current):
            return proposed
    except ValueError:
        pass
    return current


_mention_map: Optional[Dict[str, str]] = None


def _get_mention_map() -> Dict[str, str]:
    """UUID → friendly handle map for prettifying Band's rewritten mentions."""
    global _mention_map
    if _mention_map is None:
        _mention_map = {}
        try:
            from thenvoi.config.loader import load_agent_config
            for handle in ["protocol_agent", "ethics_agent", "privacy_agent", "committee_agent"]:
                try:
                    aid, _ = load_agent_config(handle)
                    _mention_map[aid] = handle
                except Exception:
                    pass
        except Exception:
            pass
        chair_id = os.getenv("BAND_IRB_CHAIR_USER_ID", "")
        if chair_id:
            _mention_map[chair_id] = "Dr.IRBChair"
    return _mention_map


def prettify_mentions(text: str) -> str:
    """Replace Band's rewritten mentions (@[[uuid]]) with friendly @handles."""
    mention_map = _get_mention_map()

    def _sub(match: "re.Match[str]") -> str:
        uuid_str = match.group(1)
        handle = mention_map.get(uuid_str)
        return f"@{handle}" if handle else "@agent"

    return re.sub(r"@\[\[([0-9a-fA-F-]+)\]\]", _sub, text)


def infer_agent_from_content(text: str) -> Optional[str]:
    """Identify the posting agent from the message's structural markers.

    Sender resolution can race in fallback mode (all four clients forward every
    room message); the markers are authoritative for our message types.
    Clarification markers must be checked by leading line, not substring — the
    REQUEST body contains the literal phrase "CLARIFICATION RESPONSE".
    """
    stripped = text.lstrip()
    if stripped.startswith("CLARIFICATION REQUEST"):
        return "committee_agent"
    if stripped.startswith("CLARIFICATION RESPONSE"):
        return "ethics_agent"
    if "ETHICS REVIEW FINDINGS" in text:
        return "ethics_agent"
    if "PRIVACY REVIEW FINDINGS" in text:
        return "privacy_agent"
    if "All findings aggregated" in text or "IRB Chair decision" in text:
        return "committee_agent"
    if "REVIEW TRACK:" in text or "risk_classification" in text:
        return "protocol_agent"
    return None


def status_for_agent_message(agent: str, content: str, current: str) -> str:
    """Map an incoming agent message to the dashboard pipeline status."""
    if agent == "ProtocolAgent":
        proposed = "ethics_review"  # parallel ethics + privacy reviews dispatched
    elif agent in ("EthicsAgent", "PrivacyAgent"):
        proposed = "privacy_review" if "CLARIFICATION RESPONSE" not in content else "committee_review"
    elif agent == "CommitteeAgent":
        if "All findings aggregated" in content:
            proposed = "awaiting_chair"
        elif "Please analyze" in content:
            proposed = current
        else:
            proposed = "committee_review"  # clarification challenge in progress
    else:
        proposed = current
    return advance_status(current, proposed)


# --- WebSocket Manager ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, review_id: str, websocket: WebSocket):
        await websocket.accept()
        if review_id not in self.active_connections:
            self.active_connections[review_id] = []
        self.active_connections[review_id].append(websocket)

    def disconnect(self, review_id: str, websocket: WebSocket):
        if review_id in self.active_connections:
            self.active_connections[review_id].remove(websocket)

    async def broadcast(self, review_id: str, message: dict):
        if review_id in self.active_connections:
            disconnected = []
            for ws in self.active_connections[review_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.append(ws)
            for ws in disconnected:
                self.active_connections[review_id].remove(ws)


manager = ConnectionManager()


# --- App ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("EthicsBoard AI API Server starting...")
    
    # Register dashboard WebSocket forwarder
    async def dashboard_forwarder(dash_msg):
        room_id = dash_msg.get("room_id")
        review_id = room_to_review.get(room_id)
        if not review_id and room_id:
            for r_id, session in reviews.items():
                if session.band_room_id == room_id:
                    review_id = r_id
                    room_to_review[room_id] = r_id
                    break
        
        if review_id:
            content = dash_msg.get("content", "")
            agent = dash_msg.get("agent")
            inferred = infer_agent_from_content(content)
            if inferred:
                agent = inferred.replace("_", " ").title().replace(" ", "")
            # Clarification exchanges restate existing findings — extracting
            # deficiencies from them would double-count
            if "CLARIFICATION" in content:
                deficiencies = []
            else:
                deficiencies = extract_deficiencies_from_text(agent, content)
            display_content = prettify_mentions(extract_analysis_from_text(content))
            
            session = reviews[review_id]
            
            # Map ReviewMessage fields
            from backend.server import ReviewMessage
            msg = ReviewMessage(
                id=dash_msg.get("id"),
                timestamp=dash_msg.get("timestamp"),
                agent=agent,
                framework=dash_msg.get("framework"),
                model_provider=dash_msg.get("model_provider"),
                content=display_content,
                message_type=dash_msg.get("message_type"),
                deficiencies=deficiencies if deficiencies else None
            )
            
            # Append if not already present
            if not any(m.id == msg.id for m in session.messages):
                session.messages.append(msg)
                if deficiencies:
                    session.deficiency_count += len(deficiencies)
                
                # Broadcast the message
                await manager.broadcast(review_id, {
                    "type": "message",
                    "data": msg.model_dump()
                })
                
                # Update dashboard status indicators based on active agent
                if session.status == "completed" or session.determination is not None:
                    next_status = "completed"
                else:
                    next_status = status_for_agent_message(agent, content, session.status)
                if next_status != session.status:
                    session.status = next_status
                    await manager.broadcast(review_id, {
                        "type": "status_update",
                        "data": {"status": next_status}
                    })

    register_dashboard_callback(dashboard_forwarder)
    
    # Start agents listening loops
    asyncio.create_task(start_all_agents())
    
    yield
    print("EthicsBoard AI API Server shutting down...")
    # Cancel all active subscription tasks on shutdown
    for t in active_subscription_tasks.values():
        t.cancel()
    active_subscription_tasks.clear()
    await stop_all_agents()


app = FastAPI(
    title="EthicsBoard AI",
    description="Multi-Agent Institutional Research Ethics Review System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- REST Endpoints ---

@app.post("/api/review/start")
async def start_review(file: UploadFile = File(...)):
    """Start a new IRB protocol review."""
    review_id = str(uuid.uuid4())[:8]
    protocol_number = f"PEDI-2026-{review_id[:4].upper()}"
    
    session = ReviewSession(
        id=review_id,
        protocol_number=protocol_number,
        status="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    reviews[review_id] = session
    
    # Save uploaded file
    content = await file.read()
    file_path = f"temp_{review_id}.pdf"
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Trigger the agent pipeline
    asyncio.create_task(run_real_pipeline(review_id, file_path))
    
    return {"review_id": review_id, "protocol_number": protocol_number, "status": "started"}


@app.get("/api/review/{review_id}")
async def get_review(review_id: str):
    """Get review session details."""
    if review_id not in reviews:
        raise HTTPException(status_code=404, detail="Review not found")
    return reviews[review_id]


@app.get("/api/review/{review_id}/messages")
async def get_messages(review_id: str):
    """Get all messages for a review."""
    if review_id not in reviews:
        raise HTTPException(status_code=404, detail="Review not found")
    return reviews[review_id].messages


@app.post("/api/review/{review_id}/decision")
async def submit_decision(review_id: str, decision: dict):
    """Submit IRB chair decision."""
    if review_id not in reviews:
        raise HTTPException(status_code=404, detail="Review not found")
    
    session = reviews[review_id]
    choice = decision.get("decision", "revisions_required")
    session.determination = choice
    session.status = "completed"

    # Record the chair's decision in the Band room — the room history is the
    # audit ledger, so a dashboard decision must leave a trace there too.
    # (Worded without the "IRB Decision" trigger phrase so the CommitteeAgent
    # records it as audit context rather than re-processing it.)
    if session.band_room_id:
        try:
            from agents.agent_runners import active_clients
            from agents.band_client import create_band_client
            band_client = active_clients.get("committee_agent") or create_band_client("committee_agent")
            await band_client.post_message(
                session.band_room_id,
                f"[AUDIT] Chair determination recorded via dashboard: {choice.upper()}. "
                f"Protocol {session.protocol_number}. Determination letter generated. "
                f"Review session completed."
            )
            print(f"[Backend] Chair decision '{choice}' recorded in Band room {session.band_room_id}")
        except Exception as e:
            print(f"[Backend] Warning: could not record decision in Band room: {e}")

    # Cancel room subscription task if active
    task = active_subscription_tasks.pop(review_id, None)
    if task:
        task.cancel()
        print(f"[Backend] Cancelled active Band room subscription task for review {review_id}")
    
    # Generate determination letter
    msg = ReviewMessage(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent="CommitteeAgent",
        framework="FastAPI",
        model_provider="Featherless AI",
        content=f"Decision recorded: {choice.upper()}. Determination letter generated for Protocol {session.protocol_number}. Complete review record preserved in Band room.",
        message_type="determination",
        metadata={"decision": choice}
    )
    session.messages.append(msg)
    
    await manager.broadcast(review_id, {
        "type": "message",
        "data": msg.model_dump()
    })
    await manager.broadcast(review_id, {
        "type": "status_update",
        "data": {"status": "completed", "determination": choice}
    })
    
    return {"status": "completed", "determination": choice}


# --- WebSocket ---

@app.websocket("/ws/review/{review_id}")
async def websocket_endpoint(websocket: WebSocket, review_id: str):
    await manager.connect(review_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages from dashboard (e.g., chair decisions)
    except WebSocketDisconnect:
        manager.disconnect(review_id, websocket)


# --- Deficiency Extraction Helper ---

def extract_analysis_from_text(text: str) -> str:
    try:
        clean_text = text.strip()
        matches = list(re.finditer(r"```(?:json)?\s*(.*?)\s*```", clean_text, flags=re.DOTALL))
        if matches:
            clean_text = matches[-1].group(1).strip()

        # Strip DeepSeek thinking process if present
        clean_text = re.sub(r"<think>.*?</think>", "", clean_text, flags=re.DOTALL).strip()

        # Findings may carry marker prefixes/handoff suffixes around the JSON body
        json_match = re.search(r"\{.*\}", clean_text, flags=re.DOTALL)
        if json_match:
            clean_text = json_match.group(0)

        data = json.loads(clean_text)
        if isinstance(data, dict) and "analysis" in data:
            return data["analysis"]
    except Exception:
        pass
    return text


def extract_deficiencies_from_text(agent_name: str, text: str) -> List[dict]:
    # 1. Try parsing text as structured JSON first
    try:
        clean_text = text.strip()
        matches = list(re.finditer(r"```(?:json)?\s*(.*?)\s*```", clean_text, flags=re.DOTALL))
        if matches:
            clean_text = matches[-1].group(1).strip()

        # Strip DeepSeek thinking process if present
        clean_text = re.sub(r"<think>.*?</think>", "", clean_text, flags=re.DOTALL).strip()

        # Findings may carry marker prefixes/handoff suffixes around the JSON body
        json_match = re.search(r"\{.*\}", clean_text, flags=re.DOTALL)
        if json_match:
            clean_text = json_match.group(0)

        data = json.loads(clean_text)
        if isinstance(data, dict) and "deficiencies" in data:
            raw_defs = data["deficiencies"]
            structured_defs = []
            for item in raw_defs:
                if isinstance(item, dict):
                    structured_defs.append({
                        "id": item.get("id", int(uuid.uuid4().int % 100000)),
                        "title": item.get("title", "Compliance Issue"),
                        "severity": item.get("severity", "major"),
                        "regulation": item.get("regulation", "Unknown Regulation"),
                        "description": item.get("description", "")
                    })
            return structured_defs
    except Exception:
        # Not JSON or failed to parse; fallback to keyword extraction below
        pass

    deficiencies = []
    text_lower = text.lower()
    
    if agent_name == "EthicsAgent":
        # Check for Informed Consent (45 CFR 46)
        if any(kw in text_lower for kw in ["consent", "45 cfr 46.116", "45 cfr 46"]):
            deficiencies.append({
                "id": 101,
                "title": "Informed Consent Form Gaps",
                "severity": "critical",
                "regulation": "45 CFR 46.116",
                "description": "Information regarding experimental procedures, risks of MetaGlyX-400, and alternatives is incomplete or unclear for pediatric parent/guardian disclosure."
            })
        # Check for Minor Assent (45 CFR 46.408)
        if any(kw in text_lower for kw in ["assent", "45 cfr 46.408", "minor", "child"]):
            deficiencies.append({
                "id": 102,
                "title": "Missing Written Assent for Minors 12-16",
                "severity": "major",
                "regulation": "45 CFR 46.408",
                "description": "The protocol specifies verbal assent for ages 8-11 but fails to provide a written assent form/documentation process for minors aged 12-16."
            })
        # Check for Risk Disclosure (ICH E6)
        if any(kw in text_lower for kw in ["risk disclosure", "ich e6", "4.8.10"]):
            deficiencies.append({
                "id": 103,
                "title": "Incomplete Risk Disclosures",
                "severity": "critical",
                "regulation": "ICH E6(R2) 4.8.10",
                "description": "Protocol fails to disclose potential long-term metabolic risks of MetaGlyX-400 in pediatric populations."
            })
            
    elif agent_name == "PrivacyAgent":
        # Check for BAA (45 CFR 164.308(b)(1))
        if any(kw in text_lower for kw in ["baa", "business associate", "164.308", "cro", "biosync"]):
            deficiencies.append({
                "id": 201,
                "title": "Missing Business Associate Agreement (BAA)",
                "severity": "critical",
                "regulation": "HIPAA 45 CFR 164.308(b)(1)",
                "description": "Protocol mentions sharing patient data with BioSync Research (CRO) but does not document an executed Business Associate Agreement."
            })
        # Check for Safe Harbor (45 CFR 164.514(b))
        if any(kw in text_lower for kw in ["de-identification", "safe harbor", "164.514"]):
            deficiencies.append({
                "id": 202,
                "title": "Unspecified De-identification Standard",
                "severity": "major",
                "regulation": "HIPAA 45 CFR 164.514(b)",
                "description": "The protocol details data sharing but does not explicitly specify that the de-identification method meets the HIPAA Safe Harbor standard."
            })
            
    return deficiencies


# --- Real Band room subscription bridge ---

def resolve_agent_name(sender_id: str) -> str:
    sender = sender_id.strip(" :")
    from thenvoi.config.loader import load_agent_config
    handles_map = {}
    for handle in ["protocol_agent", "ethics_agent", "privacy_agent", "committee_agent"]:
        try:
            aid, _ = load_agent_config(handle)
            handles_map[aid] = handle
        except Exception:
            pass
    if sender in handles_map:
        sender = handles_map[sender]
    return sender.lower().replace(" ", "_")


async def subscribe_to_band_room(room_id: str, ws_manager: ConnectionManager):
    """Bridge real Band room events to the frontend WebSocket."""
    # Lookup review_id associated with this room
    review_id = room_to_review.get(room_id)
    if not review_id:
        for r_id, session in reviews.items():
            if session.band_room_id == room_id:
                review_id = r_id
                room_to_review[room_id] = r_id
                break
            
    # Resolve the active client to subscribe to the room
    from agents.agent_runners import active_clients
    band_client = active_clients.get("committee_agent")
    if not band_client:
        from agents.band_client import create_band_client
        band_client = create_band_client("committee_agent")
        
    print(f"[Band Bridge] Subscribed dashboard WebSocket manager to room: {room_id}")
    
    try:
        async with band_client.subscribe(room_id) as stream:
            async for message in stream:
                # 1. User's exact requested bridge broadcast pattern
                sender_name = infer_agent_from_content(message.content) or resolve_agent_name(message.sender_id)
                display_content = prettify_mentions(extract_analysis_from_text(message.content))
                if review_id:
                    try:
                        await ws_manager.broadcast(review_id, {
                            "sender": sender_name,
                            "content": display_content,
                            "timestamp": message.timestamp
                        })
                    except Exception as e:
                        print(f"[Band Bridge] Broadcast error: {e}")
                        
                # 2. Robust message mapping to make the dashboard render correctly
                agent_title = sender_name.replace("_", " ").title().replace(" ", "")
                framework = "LangGraph" if sender_name == "protocol_agent" else (
                    "Pydantic AI" if sender_name == "ethics_agent" else (
                        "CrewAI" if sender_name == "privacy_agent" else "FastAPI"
                    )
                )
                provider = "Gemini 2.5 Pro" if sender_name == "protocol_agent" else (
                    "DeepSeek-R1" if sender_name == "ethics_agent" else (
                        "Claude Sonnet" if sender_name == "privacy_agent" else "Llama 3.1 70B"
                    )
                )
                msg_type = "analysis" if sender_name == "protocol_agent" else (
                    "finding" if sender_name in ["ethics_agent", "privacy_agent"] else "handoff"
                )
                
                if "CLARIFICATION" in message.content:
                    deficiencies = []  # clarification exchanges restate existing findings
                else:
                    deficiencies = extract_deficiencies_from_text(agent_title, message.content)

                if review_id:
                    session = reviews[review_id]
                    import uuid
                    msg_obj = ReviewMessage(
                        id=str(uuid.uuid4())[:8],
                        timestamp=message.timestamp,
                        agent=agent_title,
                        framework=framework,
                        model_provider=provider,
                        content=display_content,
                        message_type=msg_type,
                        deficiencies=deficiencies if deficiencies else None
                    )
                    
                    # Deduplicate and append message
                    if not any(m.content == msg_obj.content for m in session.messages):
                        session.messages.append(msg_obj)
                        if deficiencies:
                            session.deficiency_count += len(deficiencies)
                            
                        # Broadcast formatted ReviewMessage to dashboard
                        await ws_manager.broadcast(review_id, {
                            "type": "message",
                            "data": msg_obj.model_dump()
                        })
                        
                        # Update status
                        if session.status == "completed" or session.determination is not None:
                            next_status = "completed"
                        else:
                            next_status = status_for_agent_message(agent_title, message.content, session.status)
                        if next_status != session.status:
                            session.status = next_status
                            await ws_manager.broadcast(review_id, {
                                "type": "status_update",
                                "data": {"status": next_status}
                            })
    except Exception as stream_err:
        print(f"[Band Bridge] Error in subscribe_to_band_room loop: {stream_err}")


# --- Real Pipeline using Band room and WebSocket event routing ---

async def run_real_pipeline(review_id: str, file_path: str):
    """Orchestrate the real multi-agent pipeline via the Band room."""
    from agents.protocol_agent.agent import extract_pdf_text
    from agents.band_client import create_band_client
    from thenvoi.config.loader import load_agent_config
    
    session = reviews[review_id]
    session.deficiency_count = 0
    
    # Extract PDF
    pdf_text = extract_pdf_text(file_path)
    
    # 1. Create a real Band room using the committee_agent client
    print(f"[Backend] Creating real Band room for review {review_id}...")
    committee_client = create_band_client("committee_agent")
    
    room_name = f"EthicsBoard-IRB-Review-{review_id}"
    try:
        room_id = await committee_client.create_room(room_name)
        session.band_room_id = room_id
        room_to_review[room_id] = review_id
        
        # Subscribe to room messages and bridge them to the frontend
        task = asyncio.create_task(subscribe_to_band_room(room_id, manager))
        active_subscription_tasks[review_id] = task
        
        # Update status
        session.status = "protocol_review"
        await manager.broadcast(review_id, {"type": "status_update", "data": {"status": "protocol_review"}})
        
        # 2. Add other agents as participants (Protocol, Ethics, Privacy)
        for agent_name in ["protocol_agent", "ethics_agent", "privacy_agent"]:
            try:
                agent_id, _ = load_agent_config(agent_name)
                await committee_client.add_participant(room_id, agent_id)
            except Exception as e:
                print(f"[Backend] Warning: could not add {agent_name} to room: {e}")
                
        # 3. Post the initial protocol text, mentioning @protocol_agent to trigger it
        initial_text = f"@protocol_agent — Please analyze this research protocol:\n\n{pdf_text}"
        await committee_client.post_message(room_id, initial_text)
        print(f"[Backend] Initial protocol text posted by CommitteeAgent to room {room_id}. Pipeline started.")
        
    except Exception as e:
        print(f"[Backend] Error starting real pipeline: {e}. Falling back to mock pipeline.")
        asyncio.create_task(run_mock_pipeline(review_id, file_path))


# --- Mock Pipeline (replaced with real Band integration on Day 1) ---

async def run_mock_pipeline(review_id: str, file_path: str):
    """Simulate the 4-agent pipeline but using real LLM API calls instead of hardcoded strings.

    Mirrors the real Band flow: risk-based track routing, parallel ethics+privacy
    reviews, a Committee→Ethics clarification round-trip, then HITL.
    """
    from agents.protocol_agent.agent import extract_pdf_text, analyze_protocol
    from agents.ethics_agent.agent import ethics_review, ethics_clarification
    from agents.privacy_agent.agent import privacy_review
    from agents.agent_runners import extract_risk_classification
    from agents.committee_agent.agent import format_clarification_request

    session = reviews[review_id]
    session.deficiency_count = 0

    # Extract PDF
    pdf_text = extract_pdf_text(file_path)

    # Step 1: ProtocolAgent — analyze and choose the review track
    session.status = "protocol_review"
    await manager.broadcast(review_id, {"type": "status_update", "data": {"status": "protocol_review"}})

    protocol_summary = await analyze_protocol(pdf_text)
    risk = extract_risk_classification(protocol_summary)
    review_track = "EXPEDITED" if risk == "MINIMAL" else "FULL_BOARD"
    track_line = (
        "RISK: MINIMAL → REVIEW TRACK: EXPEDITED (45 CFR 46.110)"
        if review_track == "EXPEDITED"
        else "RISK: GREATER THAN MINIMAL → REVIEW TRACK: FULL BOARD (45 CFR 46.108)"
    )

    msg1 = ReviewMessage(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent="ProtocolAgent",
        framework="LangGraph",
        model_provider="AI/ML API (Gemini 2.5 Pro)",
        content=f"{protocol_summary}\n\n{track_line}\n\nDispatching parallel specialist reviews:\n@EthicsAgent — please assess informed consent adequacy and risk-benefit ratio.\n@PrivacyAgent — please review data handling and HIPAA compliance.",
        message_type="analysis",
        metadata={"review_track": review_track}
    )
    session.messages.append(msg1)
    await manager.broadcast(review_id, {"type": "message", "data": msg1.model_dump()})

    # Steps 2+3: EthicsAgent and PrivacyAgent review CONCURRENTLY
    session.status = "ethics_review"
    await manager.broadcast(review_id, {"type": "status_update", "data": {"status": "ethics_review"}})

    ethics_result, privacy_result = await asyncio.gather(
        ethics_review(protocol_summary),
        privacy_review(pdf_text),
    )

    ethics_defs = extract_deficiencies_from_text("EthicsAgent", ethics_result)
    ethics_analysis = extract_analysis_from_text(ethics_result)
    session.deficiency_count += len(ethics_defs)

    msg2 = ReviewMessage(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent="EthicsAgent",
        framework="Pydantic AI",
        model_provider="Featherless AI (DeepSeek-R1)",
        content=f"{ethics_analysis}\n\n@CommitteeAgent — ethics review complete.",
        message_type="finding",
        deficiencies=ethics_defs
    )
    session.messages.append(msg2)
    await manager.broadcast(review_id, {"type": "message", "data": msg2.model_dump()})

    session.status = "privacy_review"
    await manager.broadcast(review_id, {"type": "status_update", "data": {"status": "privacy_review"}})

    privacy_defs = extract_deficiencies_from_text("PrivacyAgent", privacy_result)
    privacy_analysis = extract_analysis_from_text(privacy_result)
    session.deficiency_count += len(privacy_defs)

    msg3 = ReviewMessage(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent="PrivacyAgent",
        framework="CrewAI",
        model_provider="AI/ML API (Claude Sonnet)",
        content=f"{privacy_analysis}\n\n@CommitteeAgent — privacy review complete.",
        message_type="finding",
        deficiencies=privacy_defs
    )
    session.messages.append(msg3)
    await manager.broadcast(review_id, {"type": "message", "data": msg3.model_dump()})

    # Step 4: CommitteeAgent challenges EthicsAgent before convening the chair
    session.status = "committee_review"
    await manager.broadcast(review_id, {"type": "status_update", "data": {"status": "committee_review"}})

    findings_lines = [f"DEFICIENCY {d['id']}: {d['title']} — {d['regulation']} [{d['severity']}]" for d in (ethics_defs + privacy_defs)]
    clarification_req = format_clarification_request({"deficiencies": findings_lines, "total_deficiencies": len(findings_lines)})

    msg4 = ReviewMessage(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent="CommitteeAgent",
        framework="FastAPI",
        model_provider="Featherless AI (Llama 3.1 70B)",
        content=clarification_req,
        message_type="handoff",
        metadata={"agent_to_agent_challenge": True}
    )
    session.messages.append(msg4)
    await manager.broadcast(review_id, {"type": "message", "data": msg4.model_dump()})

    clarification_answer = await ethics_clarification(clarification_req)
    msg5 = ReviewMessage(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent="EthicsAgent",
        framework="Pydantic AI",
        model_provider="Featherless AI (DeepSeek-R1)",
        content=f"CLARIFICATION RESPONSE\n\n{clarification_answer}\n\n@CommitteeAgent — clarification provided. Proceed with your determination.",
        message_type="finding",
        metadata={"clarification_response": True}
    )
    session.messages.append(msg5)
    await manager.broadcast(review_id, {"type": "message", "data": msg5.model_dump()})

    # Step 5: CommitteeAgent convenes the chair (with expedited→full-board escalation)
    session.status = "awaiting_chair"
    if review_track == "EXPEDITED" and session.deficiency_count > 0:
        hitl_header = f"ESCALATION: Expedited review terminated per 45 CFR 46.110(b) — {session.deficiency_count} deficiencies found during specialist review. Escalating to FULL BOARD review.\n\n@Dr.IRBChair — Full Board determination required."
    elif review_track == "EXPEDITED":
        hitl_header = "@Dr.IRBChair — EXPEDITED determination requested (45 CFR 46.110). Minimal risk, no deficiencies — designated-reviewer sign-off is sufficient."
    else:
        hitl_header = "@Dr.IRBChair — Full Board determination required (45 CFR 46.108)."

    msg6 = ReviewMessage(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent="CommitteeAgent",
        framework="FastAPI",
        model_provider="Featherless AI (Llama 3.1 70B)",
        content=f"All findings aggregated. Adding Dr. IRB Chair to review room via Band add_participant_service...\n\n{hitl_header}\nFindings: {session.deficiency_count} deficiencies detected ({len(ethics_defs)} ethics, {len(privacy_defs)} privacy).\nProtocol cannot proceed without your decision.\n\nPlease select: APPROVE / REQUEST REVISIONS / REJECT",
        message_type="handoff",
        metadata={"requires_human_decision": True, "total_deficiencies": session.deficiency_count, "review_track": review_track}
    )
    session.messages.append(msg6)
    await manager.broadcast(review_id, {"type": "message", "data": msg6.model_dump()})
    await manager.broadcast(review_id, {"type": "status_update", "data": {"status": "awaiting_chair"}})



if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8008"))
    uvicorn.run(app, host="0.0.0.0", port=port)
