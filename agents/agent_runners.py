"""Agent Runners — Live Multi-Agent Execution Layer

Wires all 4 agents (ProtocolAgent, EthicsAgent, PrivacyAgent, CommitteeAgent) to the Band platform.
Tries to use official framework adapters (LangGraph, Pydantic AI, CrewAI),
falling back to direct client handlers if dependencies are missing.
"""

import os
import asyncio
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Shared client factory
from agents.band_client import create_band_client, BandClient

# Agent logic fallbacks
from agents.protocol_agent.agent import analyze_protocol
from agents.ethics_agent.agent import ethics_review
from agents.privacy_agent.agent import privacy_review
from agents.committee_agent.agent import aggregate_findings, format_hitl_request

load_dotenv()

# Attempt to import framework adapters
try:
    from thenvoi.adapters.langgraph import LangGraphAdapter
    from thenvoi.adapters.pydantic_ai import PydanticAIAdapter
    from thenvoi.adapters.crewai import CrewAIAdapter
    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import InMemorySaver
    from pydantic_ai.models.openai import OpenAIModel
    HAS_ADAPTERS = True
except ImportError as e:
    print(f"[Agent Runners] Adapters not fully available: {e}. Running in lightweight fallback mode.")
    HAS_ADAPTERS = False

# Global state for running tasks/agents
active_runners: List[asyncio.Task] = []
active_clients: Dict[str, BandClient] = {}


# --- System Prompts for Framework Adapters ---

PROTOCOL_SYSTEM_PROMPT = """You are an IRB protocol analyst. Analyze the provided research protocol and extract:
- Study title and protocol number
- Population (age range, vulnerable status)  
- Risk classification (minimal or greater than minimal)
- Consent procedures described
- Data handling plan

Format your output as a structured JSON summary.

CRITICAL: Once the analysis is complete, you MUST call the `thenvoi_send_message` tool to post the summary to the room and ALWAYS mention `@ethics_agent` to hand off the review.
"""

ETHICS_SYSTEM_PROMPT = """You are an IRB ethics specialist. Review the provided research protocol summary for:
1. Informed consent adequacy per 45 CFR 46
2. Written assent requirements for minors (45 CFR 46.408)
3. Risk disclosure completeness (ICH E6(R2) 4.8.10)
4. Risk-benefit ratio justification

Flag every deficiency with its regulatory citation.

CRITICAL: Once the review is complete, you MUST call the `thenvoi_send_message` tool to post your findings to the room and ALWAYS mention `@privacy_agent` to hand off the review.
"""

PRIVACY_SYSTEM_PROMPT = """You are a HIPAA compliance specialist. Review the provided research protocol and summary for:
1. De-identification method — must meet HIPAA Safe Harbour (45 CFR 164.514(b))
2. Business Associate Agreements — ANY third-party data sharing (CRO, labs, vendors) REQUIRES an executed BAA.
3. Data retention policy — must be documented and reasonable
4. PHI access controls — who can see patient data?

Use plain ASCII only. No bullet characters, em-dashes, or special symbols.
Flag every deficiency with its regulatory citation.

CRITICAL: Once the review is complete, you MUST call the `thenvoi_send_message` tool to post your findings to the room and ALWAYS mention `@committee_agent` to hand off the review.
"""


# --- Callback Registry for Dashboard WebSockets ---
message_callback = None

def register_dashboard_callback(callback):
    """Register a callback to forward Band room messages to FastAPI websockets."""
    global message_callback
    message_callback = callback


# --- Lightweight Direct Handlers (Fallback/Host mode) ---

async def handle_protocol_message(msg: dict, client: BandClient):
    """ProtocolAgent direct handler."""
    text = msg.get("text", "")
    room_id = msg.get("room_id")
    sender = msg.get("sender", "").strip(" :")
    
    # Process only if it looks like a new protocol or start of review, and mentions protocol_agent
    if ("PROTOCOL TEXT:" in text or "Study:" in text or len(text) > 200) and ("@protocol_agent" in text or client.agent_id in text):
        if sender == client.agent_name or sender == client.agent_id:
            return  # Skip self-posted messages
            
        if "All findings aggregated" in text or "IRB Decision" in text:
            return  # Skip coordinator/committee messages
            
        print(f"[ProtocolAgent] Analyzing new protocol in room {room_id}...")
        try:
            await client.mark_processing(msg["id"], room_id)
            summary = await analyze_protocol(text)
            
            # Post summary and hand off to EthicsAgent
            response_text = f"{summary}\n\n@ethics_agent — please assess informed consent adequacy and risk-benefit ratio."
            await client.post_message(room_id, response_text)
            await client.mark_processed(msg["id"], room_id)
        except Exception as e:
            print(f"[ProtocolAgent] Error: {e}")
            await client.mark_failed(msg["id"], str(e), room_id)

async def handle_ethics_message(msg: dict, client: BandClient):
    """EthicsAgent direct handler."""
    text = msg.get("text", "")
    room_id = msg.get("room_id")
    sender = msg.get("sender", "").strip(" :")
    
    if "@ethics_agent" in text or client.agent_id in text:
        if sender == client.agent_name or sender == client.agent_id:
            return  # Skip self-posted messages
            
        if "All findings aggregated" in text or "IRB Decision" in text:
            return  # Skip coordinator/committee messages
            
        print(f"[EthicsAgent] Conducting ethics review in room {room_id}...")
        try:
            await client.mark_processing(msg["id"], room_id)
            findings = await ethics_review(text)
            
            # Post findings and hand off to PrivacyAgent
            response_text = f"{findings}\n\n@privacy_agent — please review data handling and HIPAA compliance."
            await client.post_message(room_id, response_text)
            await client.mark_processed(msg["id"], room_id)
        except Exception as e:
            print(f"[EthicsAgent] Error: {e}")
            await client.mark_failed(msg["id"], str(e), room_id)

async def handle_privacy_message(msg: dict, client: BandClient):
    """PrivacyAgent direct handler."""
    text = msg.get("text", "")
    room_id = msg.get("room_id")
    sender = msg.get("sender", "").strip(" :")
    
    if "@privacy_agent" in text or client.agent_id in text:
        if sender == client.agent_name or sender == client.agent_id:
            return  # Skip self-posted messages
            
        if "All findings aggregated" in text or "IRB Decision" in text:
            return  # Skip coordinator/committee messages
            
        print(f"[PrivacyAgent] Conducting HIPAA privacy review in room {room_id}...")
        try:
            await client.mark_processing(msg["id"], room_id)
            findings = await privacy_review(text)
            
            # Post findings and hand off to CommitteeAgent
            response_text = f"{findings}\n\n@committee_agent — Findings available. Human chair approval needed."
            await client.post_message(room_id, response_text)
            await client.mark_processed(msg["id"], room_id)
        except Exception as e:
            print(f"[PrivacyAgent] Error: {e}")
            await client.mark_failed(msg["id"], str(e), room_id)

async def handle_committee_message(msg: dict, client: BandClient):
    """CommitteeAgent direct handler (HITL coordinator)."""
    text = msg.get("text", "")
    room_id = msg.get("room_id")
    sender = msg.get("sender", "").strip(" :")
    
    # Load all agent configs to map agent ID to name
    from thenvoi.config.loader import load_agent_config
    agents_ids = []
    for handle in ["protocol_agent", "ethics_agent", "privacy_agent", "committee_agent"]:
        try:
            aid, _ = load_agent_config(handle)
            agents_ids.append(aid)
            agents_ids.append(handle)
        except Exception:
            pass
            
    is_decision_keyword = any(kw in text.lower() for kw in ["approve", "reject", "revision", "revisions"])
    is_irb_decision = "irb decision" in text.lower()
    
    if is_irb_decision and is_decision_keyword:
        is_human_sender = True
    else:
        is_human_sender = sender not in agents_ids
    
    # Process if explicitly mentioned or if it is a human sender in the room
    if "@committee_agent" in text or client.agent_id in text or is_human_sender:
        if (sender == client.agent_name or sender == client.agent_id) and not (is_irb_decision and is_decision_keyword):
            return  # Skip self-posted messages
            
        if is_human_sender:
            print(f"[CommitteeAgent] Received human message in room {room_id} from sender '{sender}': '{text}'")
            # This is a human IRB Chair message! Look for decision keywords
            text_lower = text.lower()
            decision = None
            if "approve" in text_lower:
                decision = "approved"
            elif "reject" in text_lower:
                decision = "rejected"
            elif "revision" in text_lower or "revisions" in text_lower:
                decision = "revisions_required"
                
            if decision:
                print(f"[CommitteeAgent] Picked up IRB Chair decision '{decision.upper()}' from room {room_id}...")
                try:
                    await client.mark_processing(msg["id"], room_id)
                    import sys
                    reviews = {}
                    manager = None
                    ReviewMessage = None
                    main_mod = sys.modules.get("__main__")
                    if main_mod and hasattr(main_mod, "reviews"):
                        reviews = main_mod.reviews
                        manager = getattr(main_mod, "manager", None)
                        ReviewMessage = getattr(main_mod, "ReviewMessage", None)
                    else:
                        from backend.server import reviews as r, manager as m, ReviewMessage as rm
                        reviews = r
                        manager = m
                        ReviewMessage = rm
                    review_id = None
                    for r_id, session in reviews.items():
                        if session.band_room_id == room_id:
                            review_id = r_id
                            break
                            
                    if review_id:
                        session = reviews[review_id]
                        session.determination = decision
                        session.status = "completed"
                        
                        # Generate determination letter message
                        msg_obj = ReviewMessage(
                            id=str(uuid.uuid4())[:8],
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            agent="CommitteeAgent",
                            framework="FastAPI",
                            model_provider="Featherless AI",
                            content=f"Decision recorded: {decision.upper()} (via Band Room). Determination letter generated for Protocol {session.protocol_number}. Complete review record preserved in Band room.",
                            message_type="determination",
                            metadata={"decision": decision}
                        )
                        session.messages.append(msg_obj)
                        
                        # Broadcast to frontend WebSocket
                        await manager.broadcast(review_id, {
                            "type": "message",
                            "data": msg_obj.model_dump()
                        })
                        await manager.broadcast(review_id, {
                            "type": "status_update",
                            "data": {"status": "completed", "determination": decision}
                        })
                        
                        # Post confirmation back to Band room
                        await client.post_message(room_id, f"[CommitteeAgent] IRB Chair decision '{decision.upper()}' recorded successfully. Determination letter generated. Review session completed.")
                        await client.mark_processed(msg["id"], room_id)
                        return
                except Exception as ex:
                    print(f"[CommitteeAgent] Error processing chair decision: {ex}")
                    await client.mark_failed(msg["id"], str(ex), room_id)
                    return
            else:
                print(f"[CommitteeAgent] Human message in room {room_id} did not contain a valid decision keyword ('approve', 'reject', 'revision').")
                return

        # Otherwise, this is a handoff message from another agent -> run standard aggregation
        print(f"[CommitteeAgent] Aggregating findings in room {room_id}...")
        try:
            await client.mark_processing(msg["id"], room_id)
            
            # Get room history to extract all deficiencies
            history = await client.get_room_history(room_id)
            messages = [m["text"] for m in history]
            
            findings = await aggregate_findings(messages)
            
            # Extract review ID from room if possible, or protocol number
            protocol_number = f"PEDI-2026-{room_id[-4:].upper()}" if len(room_id) > 4 else "PEDI-2026-0047"
            
            # Add Dr. IRB Chair to the room
            chair_user_id = os.getenv("BAND_IRB_CHAIR_USER_ID", "irb-chair-user")
            
            hitl_request = await format_hitl_request(findings, protocol_number)
            
            # Post HITL request and add chair
            await client.post_message(room_id, hitl_request)
            try:
                import re
                if chair_user_id and re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', chair_user_id):
                    await client.add_participant(room_id, chair_user_id, f"Dr. IRB Chair added to review room.")
                else:
                    print(f"[CommitteeAgent] Warning: BAND_IRB_CHAIR_USER_ID is not a valid UUID: '{chair_user_id}'. Skipping add_participant.")
            except Exception as participant_err:
                print(f"[CommitteeAgent] Warning: Failed to add Dr. IRB Chair: {participant_err}")
            await client.mark_processed(msg["id"], room_id)
        except Exception as e:
            print(f"[CommitteeAgent] Error: {e}")
            await client.mark_failed(msg["id"], str(e), room_id)


# --- Global message tracker for dashboard WS forwarding ---

async def global_message_tracker(msg: dict, agent_name: str):
    """Intercept all messages posted by clients and forward them to the dashboard WebSocket."""
    global message_callback
    if message_callback:
        # Resolve sender to standard agent name dynamically
        sender = msg.get("sender", "").strip(" :")
        
        # Load all agent configs to map agent ID to name
        from thenvoi.config.loader import load_agent_config
        handles_map = {}
        for handle in ["protocol_agent", "ethics_agent", "privacy_agent", "committee_agent"]:
            try:
                aid, _ = load_agent_config(handle)
                handles_map[aid] = handle
            except Exception:
                pass
        
        resolved_agent = sender
        if sender in handles_map:
            resolved_agent = handles_map[sender]
            
        agent_key = resolved_agent.lower().replace(" ", "_")
        
        # Fall back to parameter agent_name if sender is not one of our agents
        if agent_key not in ["protocol_agent", "ethics_agent", "privacy_agent", "committee_agent"]:
            agent_key = agent_name.lower().replace(" ", "_") if agent_name else "committee_agent"
            
        framework = "LangGraph" if agent_key == "protocol_agent" else (
            "Pydantic AI" if agent_key == "ethics_agent" else (
                "CrewAI" if agent_key == "privacy_agent" else "FastAPI"
            )
        )
        provider = "Gemini 2.5 Pro" if agent_key == "protocol_agent" else (
            "DeepSeek-R1" if agent_key == "ethics_agent" else (
                "Claude Sonnet" if agent_key == "privacy_agent" else "Llama 3.1 70B"
            )
        )
        msg_type = "analysis" if agent_key == "protocol_agent" else (
            "finding" if agent_key in ["ethics_agent", "privacy_agent"] else "handoff"
        )
        
        # Build dashboard ReviewMessage shape
        dash_msg = {
            "id": msg.get("id", str(uuid.uuid4())[:8]),
            "timestamp": msg.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "agent": agent_key.replace("_", " ").title().replace(" ", ""),
            "framework": framework,
            "model_provider": provider,
            "content": msg.get("text", ""),
            "message_type": msg_type,
            "room_id": msg.get("room_id")
        }
        try:
            if asyncio.iscoroutinefunction(message_callback):
                await message_callback(dash_msg)
            else:
                message_callback(dash_msg)
        except Exception as e:
            print(f"[Dashboard Callback] Error: {e}")


# --- Start & Stop Agent Orchestrator ---

async def start_all_agents():
    """Start listening loops for all 4 agents."""
    print(f"Starting all agents. Adapters Available: {HAS_ADAPTERS}")
    
    if HAS_ADAPTERS:
        # 1. Wire ProtocolAgent via LangGraphAdapter
        try:
            llm = ChatOpenAI(
                model=os.getenv("GEMINI_MODEL", "google/gemini-2.5-pro"),
                api_key=os.getenv("AIML_API_KEY"),
                base_url=os.getenv("AIML_BASE_URL", "https://api.aimlapi.com/v1"),
            )
            protocol_adapter = LangGraphAdapter(
                llm=llm,
                checkpointer=InMemorySaver(),
                custom_section=PROTOCOL_SYSTEM_PROMPT,
            )
            # Create client
            client_p = create_band_client("protocol_agent")
            from thenvoi import Agent
            agent_p = Agent.create(
                adapter=protocol_adapter,
                agent_id=client_p.agent_id,
                api_key=client_p.api_key,
                ws_url=os.getenv("THENVOI_WS_URL", "wss://app.band.ai/api/v1/socket/websocket"),
                rest_url=os.getenv("THENVOI_REST_URL", "https://app.band.ai"),
            )
            active_runners.append(asyncio.create_task(agent_p.start()))
            print("[Agent Runners] ProtocolAgent wired via LangGraphAdapter.")
        except Exception as e:
            print(f"[Agent Runners] Failed to wire ProtocolAgent: {e}")

        # 2. Wire EthicsAgent via PydanticAIAdapter
        try:
            model = OpenAIModel(
                model_name="deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
                api_key=os.getenv("FEATHERLESS_API_KEY"),
                base_url=os.getenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1"),
            )
            ethics_adapter = PydanticAIAdapter(
                model=model,
                custom_section=ETHICS_SYSTEM_PROMPT,
            )
            client_e = create_band_client("ethics_agent")
            from thenvoi import Agent
            agent_e = Agent.create(
                adapter=ethics_adapter,
                agent_id=client_e.agent_id,
                api_key=client_e.api_key,
                ws_url=os.getenv("THENVOI_WS_URL", "wss://app.band.ai/api/v1/socket/websocket"),
                rest_url=os.getenv("THENVOI_REST_URL", "https://app.band.ai"),
            )
            active_runners.append(asyncio.create_task(agent_e.start()))
            print("[Agent Runners] EthicsAgent wired via PydanticAIAdapter.")
        except Exception as e:
            print(f"[Agent Runners] Failed to wire EthicsAgent: {e}")

        # 3. Wire PrivacyAgent via CrewAIAdapter
        try:
            # Set environment variables for CrewAI's LLM
            os.environ["OPENAI_API_BASE"] = os.getenv("AIML_BASE_URL", "https://api.aimlapi.com/v1")
            os.environ["OPENAI_API_KEY"] = os.getenv("AIML_API_KEY", "")
            
            privacy_adapter = CrewAIAdapter(
                model="openai/claude-sonnet-4-6",
                role="HIPAA compliance specialist",
                goal="Review research protocols for HIPAA Safe Harbor and CRO BAA compliance",
                backstory=PRIVACY_SYSTEM_PROMPT,
            )
            client_pr = create_band_client("privacy_agent")
            from thenvoi import Agent
            agent_pr = Agent.create(
                adapter=privacy_adapter,
                agent_id=client_pr.agent_id,
                api_key=client_pr.api_key,
                ws_url=os.getenv("THENVOI_WS_URL", "wss://app.band.ai/api/v1/socket/websocket"),
                rest_url=os.getenv("THENVOI_REST_URL", "https://app.band.ai"),
            )
            active_runners.append(asyncio.create_task(agent_pr.start()))
            print("[Agent Runners] PrivacyAgent wired via CrewAIAdapter.")
        except Exception as e:
            print(f"[Agent Runners] Failed to wire PrivacyAgent: {e}")

        # 4. Wire CommitteeAgent via Direct Client Loop
        try:
            client_c = create_band_client("committee_agent")
            
            @client_c.on_message
            async def on_comm_msg(msg):
                await handle_committee_message(msg, client_c)
                await global_message_tracker(msg, "committee_agent")
                
            active_runners.append(asyncio.create_task(client_c.run()))
            active_clients["committee_agent"] = client_c
            print("[Agent Runners] CommitteeAgent wired via direct client loop.")
        except Exception as e:
            print(f"[Agent Runners] Failed to wire CommitteeAgent: {e}")

    else:
        # Fallback Mode: Wire all 4 using direct client event listeners
        agents = ["protocol_agent", "ethics_agent", "privacy_agent", "committee_agent"]
        handlers = {
            "protocol_agent": handle_protocol_message,
            "ethics_agent": handle_ethics_message,
            "privacy_agent": handle_privacy_message,
            "committee_agent": handle_committee_message,
        }
        
        for name in agents:
            try:
                client = create_band_client(name)
                
                # Register handler using closure to capture name and client
                def make_handler(agent_name, agent_client, core_handler):
                    async def handler(msg):
                        # Forward output to dashboard WS
                        await global_message_tracker(msg, agent_name)
                        # Process response if mention triggers
                        await core_handler(msg, agent_client)
                    return handler
                
                client.on_message(make_handler(name, client, handlers[name]))
                
                # Start listener task
                task = asyncio.create_task(client.run())
                active_runners.append(task)
                active_clients[name] = client
                print(f"[Agent Runners] Start fallback client for {name}.")
            except Exception as e:
                print(f"[Agent Runners] Failed to start {name} in fallback mode: {e}")


async def stop_all_agents():
    """Stop all running listening loops."""
    print("Stopping all agents...")
    # Stop clients
    for client in active_clients.values():
        client.stop()
    # Cancel tasks
    for task in active_runners:
        task.cancel()
    active_runners.clear()
    active_clients.clear()
    print("All agents stopped.")
