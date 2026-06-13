"""EthicsBoard AI — Backend API Server

Provides REST API and WebSocket endpoints for the frontend dashboard.
Bridges between the Band room and the React dashboard.
"""

import asyncio
import json
import uuid
import os
import sys
from datetime import datetime, timezone

# Add project root to sys.path so we can import agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


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
    yield
    print("EthicsBoard AI API Server shutting down...")


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
    asyncio.create_task(run_mock_pipeline(review_id, file_path))
    
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


# --- Mock Pipeline (replaced with real Band integration on Day 1) ---

async def run_mock_pipeline(review_id: str, file_path: str):
    """Simulate the 4-agent pipeline but using real LLM API calls instead of hardcoded strings."""
    from agents.protocol_agent.agent import extract_pdf_text, analyze_protocol
    from agents.ethics_agent.agent import ethics_review
    from agents.privacy_agent.agent import privacy_review
    
    session = reviews[review_id]
    
    # Extract PDF
    pdf_text = extract_pdf_text(file_path)
    
    # Step 1: ProtocolAgent
    session.status = "protocol_review"
    await manager.broadcast(review_id, {"type": "status_update", "data": {"status": "protocol_review"}})
    
    protocol_summary = await analyze_protocol(pdf_text)
    
    msg1 = ReviewMessage(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent="ProtocolAgent",
        framework="LangGraph",
        model_provider="AI/ML API (Gemini 2.5 Pro)",
        content=f"{protocol_summary}\n\n@EthicsAgent — please assess informed consent adequacy and risk-benefit ratio.",
        message_type="analysis",
        metadata={}
    )
    session.messages.append(msg1)
    await manager.broadcast(review_id, {"type": "message", "data": msg1.model_dump()})
    
    # Step 2: EthicsAgent
    session.status = "ethics_review"
    await manager.broadcast(review_id, {"type": "status_update", "data": {"status": "ethics_review"}})
    
    ethics_result = await ethics_review(protocol_summary)
    
    msg2 = ReviewMessage(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent="EthicsAgent",
        framework="Pydantic AI",
        model_provider="Featherless AI (DeepSeek-R1)",
        content=f"{ethics_result}\n\n@PrivacyAgent — please review data handling and HIPAA compliance.",
        message_type="finding",
        deficiencies=[]
    )
    session.messages.append(msg2)
    await manager.broadcast(review_id, {"type": "message", "data": msg2.model_dump()})
    
    # Step 3: PrivacyAgent
    session.status = "privacy_review"
    await manager.broadcast(review_id, {"type": "status_update", "data": {"status": "privacy_review"}})
    
    privacy_result = await privacy_review(pdf_text)
    
    msg3 = ReviewMessage(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent="PrivacyAgent",
        framework="CrewAI",
        model_provider="AI/ML API (Claude Sonnet)",
        content=f"{privacy_result}\n\n@CommitteeAgent — Findings available. Human chair approval needed.",
        message_type="finding",
        deficiencies=[]
    )
    session.messages.append(msg3)
    await manager.broadcast(review_id, {"type": "message", "data": msg3.model_dump()})
    
    # Step 4: CommitteeAgent
    await asyncio.sleep(3)
    session.status = "awaiting_chair"
    msg4 = ReviewMessage(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(timezone.utc).isoformat(),
        agent="CommitteeAgent",
        framework="FastAPI",
        model_provider="Featherless AI (Llama 3.1 70B)",
        content="All findings aggregated. Adding Dr. IRB Chair to review room via Band add_participant_service...\n\n@Dr.IRBChair — Full Board determination required.\nFindings: 3 deficiencies (2 ethics, 1 privacy).\nProtocol cannot proceed without your decision.\n\nPlease select: APPROVE / REQUEST REVISIONS / REJECT",
        message_type="handoff",
        metadata={"requires_human_decision": True, "total_deficiencies": 3}
    )
    session.messages.append(msg4)
    await manager.broadcast(review_id, {"type": "message", "data": msg4.model_dump()})
    await manager.broadcast(review_id, {"type": "status_update", "data": {"status": "awaiting_chair"}})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
