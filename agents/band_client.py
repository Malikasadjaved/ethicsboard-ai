"""Band Client — Shared Band SDK Integration Layer

This module provides a unified interface for all agents to communicate
through Band. During pre-hackathon development, it uses a mock implementation.
On Day 1 of the hackathon, swap MockBandClient for the real thenvoi-sdk.

The real implementation will use:
  from thenvoi import Agent
  from thenvoi.adapters import LangGraphAdapter, ClaudeSDKAdapter, etc.
"""

import os
import asyncio
import json
from datetime import datetime, timezone
from typing import Callable, Optional, List, Dict
from dotenv import load_dotenv

load_dotenv()


class MockBandClient:
    """Mock Band client for pre-hackathon development.
    
    Simulates Band room communication locally.
    Replace with real thenvoi-sdk integration on Day 1.
    """
    
    def __init__(self, agent_id: str, api_key: str, agent_name: str = "Agent"):
        self.agent_id = agent_id
        self.api_key = api_key
        self.agent_name = agent_name
        self.rooms: Dict[str, List[dict]] = {}
        self.message_handlers: List[Callable] = []
        self._running = False
    
    async def create_room(self, room_name: str) -> str:
        """Create a new Band room."""
        room_id = f"mock-room-{room_name}"
        self.rooms[room_id] = []
        print(f"[Band Mock] Room created: {room_name} ({room_id})")
        return room_id
    
    async def join_room(self, room_id: str):
        """Join an existing Band room."""
        if room_id not in self.rooms:
            self.rooms[room_id] = []
        print(f"[Band Mock] {self.agent_name} joined room {room_id}")
    
    async def post_message(self, room_id: str, text: str) -> dict:
        """Post a message to a Band room."""
        message = {
            "id": f"msg-{len(self.rooms.get(room_id, []))+1}",
            "room_id": room_id,
            "sender": self.agent_name,
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if room_id not in self.rooms:
            self.rooms[room_id] = []
        self.rooms[room_id].append(message)
        print(f"[Band Mock] {self.agent_name} posted to {room_id}: {text[:80]}...")
        return message
    
    async def get_room_history(self, room_id: str) -> List[dict]:
        """Get all messages in a Band room (context sharing)."""
        return self.rooms.get(room_id, [])
    
    async def add_participant(self, room_id: str, user_id: str, message: str = ""):
        """Add a participant (human or agent) to a Band room."""
        print(f"[Band Mock] Added participant {user_id} to room {room_id}")
        if message:
            await self.post_message(room_id, f"[System] {message}")
    
    async def mark_processing(self, message_id: str):
        """Mark a message as being processed."""
        print(f"[Band Mock] Message {message_id} marked as processing")
    
    async def mark_processed(self, message_id: str):
        """Mark a message as processed."""
        print(f"[Band Mock] Message {message_id} marked as processed")
    
    async def mark_failed(self, message_id: str, error: str = ""):
        """Mark a message processing as failed."""
        print(f"[Band Mock] Message {message_id} marked as failed: {error}")
    
    def on_message(self, handler: Callable):
        """Register a message handler (decorator)."""
        self.message_handlers.append(handler)
        return handler
    
    async def run(self):
        """Start listening for messages (mock version just waits)."""
        self._running = True
        print(f"[Band Mock] {self.agent_name} is running and listening...")
        while self._running:
            await asyncio.sleep(1)
    
    def stop(self):
        """Stop the agent."""
        self._running = False


# --- Factory ---

def create_band_client(agent_name: str) -> MockBandClient:
    """Create a Band client for the given agent.
    
    In production (hackathon Day 1+), this will return a real thenvoi Agent:
    
        from thenvoi import Agent
        from thenvoi.config import load_agent_config
        
        agent_id, api_key = load_agent_config(agent_name)
        return Agent.create(
            adapter=adapter,
            agent_id=agent_id,
            api_key=api_key,
            ws_url=os.getenv('BAND_WS_URL'),
            rest_url=os.getenv('BAND_REST_URL'),
        )
    """
    agent_id = os.getenv(f"BAND_{agent_name.upper()}_AGENT_ID", f"mock-{agent_name}")
    api_key = os.getenv(f"BAND_{agent_name.upper()}_API_KEY", "mock-key")
    
    return MockBandClient(
        agent_id=agent_id,
        api_key=api_key,
        agent_name=agent_name,
    )
