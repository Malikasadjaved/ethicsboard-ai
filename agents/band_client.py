"""Band Client — Shared Band SDK Integration Layer

This module provides a unified interface for all agents to communicate
through Band. Swapped from mock to real thenvoi-sdk.
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import Callable, Optional, List, Dict
from dotenv import load_dotenv

# Real thenvoi SDK imports
from thenvoi import Agent
from thenvoi.config.loader import load_agent_config
from thenvoi.core.simple_adapter import SimpleAdapter
from thenvoi.client.rest import AsyncRestClient
from thenvoi_rest import ChatMessageRequest, ParticipantRequest

load_dotenv()


class BandClientAdapter(SimpleAdapter[list]):
    """Bridge SimpleAdapter callbacks to BandClient's custom message handlers."""
    
    def __init__(self, client: 'BandClient'):
        super().__init__()
        self.client = client

    async def on_message(
        self,
        msg,
        tools,
        history,
        participants_msg,
        contacts_msg,
        *,
        is_session_bootstrap,
        room_id,
    ) -> None:
        # Convert platform message to matching dictionary format
        mapped_msg = {
            "id": msg.id,
            "room_id": room_id,
            "sender": msg.sender_name or msg.sender_id,
            "text": msg.content,
            "timestamp": msg.inserted_at.isoformat() if msg.inserted_at else datetime.now(timezone.utc).isoformat(),
        }
        for handler in self.client.message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(mapped_msg)
                else:
                    handler(mapped_msg)
            except Exception as e:
                print(f"[Band Client Adapter] Error in message handler: {e}")


class BandClient:
    """Production Band client using the real thenvoi-sdk.
    
    Wraps both REST client and WS Agent loop for communication.
    """
    
    def __init__(self, agent_id: str, api_key: str, agent_name: str = "Agent"):
        self.agent_id = agent_id
        self.api_key = api_key
        self.agent_name = agent_name
        self.message_handlers: List[Callable] = []
        self._running = False
        self.agent = None
        self.adapter = None
        
        # Initialize AsyncRestClient
        rest_url = os.getenv("THENVOI_REST_URL", "https://app.band.ai").rstrip('/')
        self.rest_client = AsyncRestClient(
            api_key=self.api_key,
            base_url=rest_url,
        )
    
    async def create_room(self, room_name: str) -> str:
        """Create a new Band room."""
        from thenvoi_rest import ChatRoomRequest
        try:
            resp = await self.rest_client.agent_api_chats.create_agent_chat(
                chat=ChatRoomRequest(task_id=room_name)
            )
            room_id = resp.data.id
            print(f"[Band Client] Room created: {room_name} ({room_id})")
            return room_id
        except Exception as e:
            print(f"[Band Client] Error creating room {room_name}: {e}")
            raise e
    
    async def join_room(self, room_id: str):
        """Join an existing Band room.
        
        Adding a participant automatically joins them on the platform.
        """
        print(f"[Band Client] {self.agent_name} joining room {room_id}")
    
    async def post_message(self, room_id: str, text: str) -> dict:
        """Post a message to a Band room."""
        try:
            resp = await self.rest_client.agent_api_messages.create_agent_chat_message(
                chat_id=room_id,
                message=ChatMessageRequest(content=text, mentions=[])
            )
            message = {
                "id": resp.data.id,
                "room_id": room_id,
                "sender": self.agent_name,
                "text": text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            print(f"[Band Client] {self.agent_name} posted to {room_id}: {text[:80]}...")
            return message
        except Exception as e:
            print(f"[Band Client] Error posting message to room {room_id}: {e}")
            raise e
    
    async def get_room_history(self, room_id: str) -> List[dict]:
        """Get all messages in a Band room (context sharing)."""
        try:
            resp = await self.rest_client.agent_api_messages.list_agent_messages(
                chat_id=room_id,
                status='all'
            )
            history = []
            for msg in resp.data:
                history.append({
                    "id": msg.id,
                    "room_id": room_id,
                    "sender": msg.sender_name or msg.sender_id,
                    "text": msg.content,
                    "timestamp": msg.inserted_at.isoformat() if msg.inserted_at else None,
                })
            return history
        except Exception as e:
            print(f"[Band Client] Error fetching room history for {room_id}: {e}")
            return []
    
    async def add_participant(self, room_id: str, user_id: str, message: str = ""):
        """Add a participant (human or agent) to a Band room."""
        try:
            await self.rest_client.agent_api_participants.add_agent_chat_participant(
                chat_id=room_id,
                participant=ParticipantRequest(participant_id=user_id, role='member')
            )
            print(f"[Band Client] Added participant {user_id} to room {room_id}")
            if message:
                await self.post_message(room_id, f"[System] {message}")
        except Exception as e:
            print(f"[Band Client] Error adding participant {user_id} to room {room_id}: {e}")
            raise e
    
    async def mark_processing(self, message_id: str, room_id: Optional[str] = None):
        """Mark a message as being processed."""
        if room_id:
            try:
                await self.rest_client.agent_api_messages.mark_agent_message_processing(
                    chat_id=room_id,
                    id=message_id
                )
                print(f"[Band Client] Message {message_id} marked as processing")
            except Exception as e:
                print(f"[Band Client] Error marking message {message_id} as processing: {e}")
    
    async def mark_processed(self, message_id: str, room_id: Optional[str] = None):
        """Mark a message as processed."""
        if room_id:
            try:
                await self.rest_client.agent_api_messages.mark_agent_message_processed(
                    chat_id=room_id,
                    id=message_id
                )
                print(f"[Band Client] Message {message_id} marked as processed")
            except Exception as e:
                print(f"[Band Client] Error marking message {message_id} as processed: {e}")
    
    async def mark_failed(self, message_id: str, error: str = "", room_id: Optional[str] = None):
        """Mark a message processing as failed."""
        if room_id:
            try:
                await self.rest_client.agent_api_messages.mark_agent_message_failed(
                    chat_id=room_id,
                    id=message_id,
                    error=error
                )
                print(f"[Band Client] Message {message_id} marked as failed: {error}")
            except Exception as e:
                print(f"[Band Client] Error marking message {message_id} as failed: {e}")
    
    def on_message(self, handler: Callable):
        """Register a message handler (decorator)."""
        self.message_handlers.append(handler)
        return handler
    
    async def run(self):
        """Start listening for messages via the WebSocket Agent runtime."""
        self._running = True
        self.adapter = BandClientAdapter(self)
        
        ws_url = os.getenv("THENVOI_WS_URL", "wss://app.band.ai/api/v1/socket/websocket")
        rest_url = os.getenv("THENVOI_REST_URL", "https://app.band.ai").rstrip('/')
        
        self.agent = Agent.create(
            adapter=self.adapter,
            agent_id=self.agent_id,
            api_key=self.api_key,
            ws_url=ws_url,
            rest_url=rest_url,
        )
        
        print(f"[Band Client] Starting real Agent {self.agent_name}...")
        await self.agent.start()
        
        try:
            while self._running:
                await asyncio.sleep(0.5)
        finally:
            await self.agent.stop()
            print(f"[Band Client] Real Agent {self.agent_name} stopped.")
    
    def stop(self):
        """Stop the agent."""
        self._running = False


# --- Factory ---

def create_band_client(agent_name: str) -> BandClient:
    """Create a Band client for the given agent name."""
    try:
        agent_id, api_key = load_agent_config(agent_name)
    except Exception as e:
        print(f"[Band Client] Failed to load agent config for {agent_name} from yaml: {e}. Falling back to env vars.")
        agent_id = os.getenv(f"BAND_{agent_name.upper()}_AGENT_ID", f"mock-{agent_name}")
        api_key = os.getenv(f"BAND_{agent_name.upper()}_API_KEY", "mock-key")
        
    return BandClient(
        agent_id=agent_id,
        api_key=api_key,
        agent_name=agent_name,
    )
