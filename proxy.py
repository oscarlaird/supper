#%%
import nest_asyncio
nest_asyncio.apply()
import asyncio
import json
from websockets.server import serve
from urllib.parse import urlparse, parse_qs

# Store sessions as {session_id: {"extension": ws, "playwright": ws}}
sessions = {}

async def handle_connection(websocket, path):
    print(f"WebSocket connection received on path: {path}")

    try:
        parsed_path = urlparse(path)
        route = parsed_path.path
        query = parse_qs(parsed_path.query)
        session_id = query.get("sessionId", [None])[0]

        if not session_id:
            await websocket.send("Missing sessionId")
            await websocket.close()
            return

        print(f"Client connected to {route} with sessionId={session_id}")

        if session_id not in sessions:
            sessions[session_id] = {}

        if route == "/extension":
            sessions[session_id]["extension"] = websocket
        elif route == "/playwright":
            sessions[session_id]["playwright"] = websocket
        else:
            print(f"Unknown client type: {route}")
            await websocket.close()
            return

        await relay_messages(websocket, session_id)
    except Exception as e:
        print(f"Error handling connection: {e}")
    finally:
        # Clean up
        for sid, conn in sessions.items():
            if conn.get("extension") == websocket:
                print(f"Extension for session {sid} disconnected")
                conn["extension"] = None
            if conn.get("playwright") == websocket:
                print(f"Playwright for session {sid} disconnected")
                conn["playwright"] = None
        # Optionally remove empty sessions
        sessions_copy = dict(sessions)
        for sid, conn in sessions_copy.items():
            if not conn.get("extension") and not conn.get("playwright"):
                del sessions[sid]

async def relay_messages(source_ws, session_id):
    try:
        async for message in source_ws:
            conn = sessions.get(session_id, {})
            target_ws = None

            if conn.get("extension") == source_ws:
                target_ws = conn.get("playwright")
                sender = "Extension"
            elif conn.get("playwright") == source_ws:
                target_ws = conn.get("extension")
                sender = "Playwright"
            else:
                print(f"Unknown source websocket for session {session_id}")
                return

            print(f"Received from {sender} (session {session_id}): {message}")

            if target_ws:
                await target_ws.send(message)
            else:
                print(f"No target connected in session {session_id}")
    except Exception as e:
        print(f"Error relaying messages in session {session_id}: {e}")

async def main():
    server = await serve(handle_connection, "0.0.0.0", 9223, max_size=1024*1024*10)
    print("WebSocket proxy server started on 0.0.0.0:9223")
    print("Connect with: ws://<host>:9223/extension?sessionId=xyz")
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

# %%
