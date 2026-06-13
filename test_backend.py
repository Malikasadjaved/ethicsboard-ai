import asyncio
import httpx
import websockets
import json
import os

backend_url = "http://localhost:8000"
ws_url = "ws://localhost:8000"

async def test_full_flow():
    # 1. Read sample protocol
    protocol_path = r"D:\Hackathone band\demo\IRB_Protocol_PEDI-2026-0047.pdf"
    if not os.path.exists(protocol_path):
        print(f"Error: {protocol_path} does not exist.")
        return
        
    print(f"Reading sample protocol from {protocol_path}...")
    with open(protocol_path, "rb") as f:
        file_content = f.read()

    # 2. Start review session by calling REST API
    async with httpx.AsyncClient() as client:
        print("Starting review session via REST API...")
        response = await client.post(
            f"{backend_url}/api/review/start",
            files={"file": ("IRB_Protocol_PEDI-2026-0047.pdf", file_content, "application/pdf")}
        )
        if response.status_code != 200:
            print(f"Failed to start review: {response.text}")
            return
            
        data = response.json()
        review_id = data["review_id"]
        protocol_number = data["protocol_number"]
        print(f"Review session started successfully!")
        print(f"Review ID: {review_id}")
        print(f"Protocol Number: {protocol_number}")

    # 3. Connect to WebSocket to receive real-time updates
    websocket_uri = f"{ws_url}/ws/review/{review_id}"
    print(f"Connecting to WebSocket: {websocket_uri}...")
    
    async with websockets.connect(websocket_uri) as ws:
        print("Connected to WebSocket. Listening for real-time messages from agents...")
        
        # We expect a series of messages: ProtocolAgent -> EthicsAgent -> PrivacyAgent -> CommitteeAgent
        try:
            while True:
                message_str = await asyncio.wait_for(ws.recv(), timeout=120.0)
                message = json.loads(message_str)
                msg_type = message.get("type")
                
                if msg_type == "message":
                    data = message.get("data", {})
                    agent = data.get("agent")
                    msg_type_str = data.get("message_type")
                    content = data.get("content", "")
                    deficiencies = data.get("deficiencies")
                    
                    print(f"\n[Message from {agent}] (Type: {msg_type_str})")
                    print(f"Content: {content[:200]}...")
                    if deficiencies:
                        print(f"Deficiencies detected: {len(deficiencies)}")
                        for d in deficiencies:
                            print(f"  - {d.get('title')} ({d.get('regulation')}) [{d.get('severity')}]")
                            
                elif msg_type == "status_update":
                    status = message.get("data", {}).get("status")
                    print(f"\n>>> Status Update: {status}")
                    
                    if status == "awaiting_chair":
                        print("\nPipeline finished running! Session is now awaiting chair decision.")
                        break
        except asyncio.TimeoutError:
            print("Timeout waiting for WebSocket messages.")
            return

    # 4. Submit chair decision via REST API
    async with httpx.AsyncClient() as client:
        print("\nSubmitting chair decision: revisions_required...")
        decision_payload = {"decision": "revisions_required"}
        response = await client.post(
            f"{backend_url}/api/review/{review_id}/decision",
            json=decision_payload
        )
        if response.status_code != 200:
            print(f"Failed to submit decision: {response.text}")
            return
            
        result = response.json()
        print(f"Decision submission response: {result}")

    # 5. Connect again to check final status and final messages
    async with httpx.AsyncClient() as client:
        print("\nChecking final review session details...")
        response = await client.get(f"{backend_url}/api/review/{review_id}")
        if response.status_code != 200:
            print(f"Failed to retrieve session details: {response.text}")
            return
            
        session_details = response.json()
        print(f"Final Session Status: {session_details.get('status')}")
        print(f"Final Session Determination: {session_details.get('determination')}")
        print(f"Total Messages: {len(session_details.get('messages', []))}")
        print(f"Total Deficiencies: {session_details.get('deficiency_count')}")

if __name__ == "__main__":
    asyncio.run(test_full_flow())
