"""
Local poll server for ITE presentations.
Serves HTML + WebSocket for real-time voting. No signup, free.

Usage:
  1. pip install fastapi uvicorn
  2. python poll_server.py
  3. Open http://localhost:8765
  4. Audience on same WiFi: http://YOUR_IP:8765
"""

import json
import webbrowser
from pathlib import Path
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    import uvicorn
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

PORT = 8765
BASE_DIR = Path(__file__).parent / "ITE_HTML"
BASE_DIR.mkdir(parents=True, exist_ok=True)

poll_votes = {}
presenter_clients = set()


@asynccontextmanager
async def lifespan(app):
    yield
    presenter_clients.clear()
    poll_votes.clear()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    """Serve index with list of presentations, or first one."""
    index_path = BASE_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    files = list(BASE_DIR.glob("*.html"))
    if not files:
        return {"message": "Run create_ite_html.py first.", "files": []}
    return FileResponse(BASE_DIR / sorted(f.name for f in files)[0])


@app.get("/{filename}")
async def serve_file(filename: str):
    path = BASE_DIR / filename
    if path.exists() and path.is_file():
        return FileResponse(path)
    return {"error": "Not found"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    role = "audience"
    current_poll = None

    try:
        msg = await websocket.receive_text()
        data = json.loads(msg)
        role = data.get("role", "audience")
        current_poll = data.get("poll")

        if role == "presenter":
            presenter_clients.add(websocket)
            # Send list of presentations
            files = sorted(BASE_DIR.glob("*.html"))
            await websocket.send_json({"type": "ready", "files": [f.name for f in files]})
        else:
            if current_poll and current_poll in poll_votes:
                await websocket.send_json({
                    "type": "results", "poll": current_poll,
                    "votes": poll_votes[current_poll],
                })

        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)
            if data.get("type") == "vote":
                poll_id = data.get("poll")
                choice = data.get("choice")
                if poll_id and choice:
                    if poll_id not in poll_votes:
                        poll_votes[poll_id] = {}
                    poll_votes[poll_id][choice] = poll_votes[poll_id].get(choice, 0) + 1
                    for client in presenter_clients:
                        try:
                            await client.send_json({
                                "type": "results", "poll": poll_id,
                                "votes": dict(poll_votes[poll_id]),
                            })
                        except Exception:
                            pass
            elif data.get("type") == "reset":
                poll_id = data.get("poll")
                if poll_id:
                    poll_votes[poll_id] = {}
                    for client in presenter_clients:
                        try:
                            await client.send_json({"type": "reset", "poll": poll_id})
                        except Exception:
                            pass
            elif data.get("type") == "poll_change":
                current_poll = data.get("poll")

    except WebSocketDisconnect:
        pass
    finally:
        presenter_clients.discard(websocket)


def main():
    if not HAS_DEPS:
        print("Install: pip install fastapi uvicorn")
        return 1
    print(f"\n  Interactive poll server")
    print(f"  Open: http://localhost:{PORT}")
    print(f"  Same WiFi: http://YOUR_IP:{PORT}")
    print(f"  Ctrl+C to stop\n")
    try:
        webbrowser.open(f"http://localhost:{PORT}/")
    except Exception:
        pass
    uvicorn.run(app, host="0.0.0.0", port=PORT)
    return 0


if __name__ == "__main__":
    exit(main())
