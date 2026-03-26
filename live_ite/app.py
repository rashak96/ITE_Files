"""
Live ITE: FastAPI + WebSocket. Presenter deck + phone voting; results broadcast live.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse

STATIC = Path(__file__).parent / "static"

# Browsers (and some proxies) cache static files aggressively — without this, deploys look "stuck" on old UI.
_NO_CACHE = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}

app = FastAPI()


def _missing_static(name: str) -> HTMLResponse:
    return HTMLResponse(
        content=(
            f"<h1>Missing file: live_ite/static/{name}</h1>"
            "<p>The server is running, but this file was not deployed. "
            "Push the whole <code>live_ite/static/</code> folder to GitHub "
            "(presenter.html, vote.html, data.json) and redeploy on Render.</p>"
        ),
        status_code=503,
    )


@app.get("/health")
async def health():
    return {"ok": True, "static_dir": str(STATIC), "presenter": (STATIC / "presenter.html").is_file()}
votes: dict[str, dict[str, int]] = {}
active_poll: str | None = None
voting_open: bool = False
# Snapshot pushed by presenter so phones never rely on stale local data.json
active_question: dict | None = None
clients: set[WebSocket] = set()


async def broadcast(payload: dict) -> None:
    dead: list[WebSocket] = []
    for ws in clients:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)


@app.get("/")
async def presenter():
    p = STATIC / "presenter.html"
    if not p.is_file():
        return _missing_static("presenter.html")
    return FileResponse(p, headers=_NO_CACHE)


@app.get("/vote")
async def vote_page():
    p = STATIC / "vote.html"
    if not p.is_file():
        return _missing_static("vote.html")
    return FileResponse(p, headers=_NO_CACHE)


@app.get("/present")
async def present_simple():
    """Button-driven presenter (no slide deck); same /vote + WebSocket as /."""
    p = STATIC / "simple.html"
    if not p.is_file():
        return _missing_static("simple.html")
    return FileResponse(p, headers=_NO_CACHE)


@app.get("/data.json")
async def data_json():
    p = STATIC / "data.json"
    if not p.is_file():
        return _missing_static("data.json")
    return FileResponse(p, headers=_NO_CACHE)


@app.get("/api/state")
async def api_state():
    return {
        "votes": {k: dict(v) for k, v in votes.items()},
        "active_poll": active_poll,
        "voting_open": voting_open,
        "active_question": active_question,
        "public_url": os.environ.get("PUBLIC_BASE_URL", ""),
    }


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    global active_poll, voting_open, active_question
    await ws.accept()
    clients.add(ws)
    try:
        await ws.send_json(
            {
                "type": "sync",
                "votes": {k: dict(v) for k, v in votes.items()},
                "active_poll": active_poll,
                "voting_open": voting_open,
                "active_question": active_question,
            }
        )
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")

            if mtype == "active_poll":
                active_poll = msg.get("poll_id")
                voting_open = bool(msg.get("voting", True))
                q = msg.get("question")
                active_question = q if isinstance(q, dict) else None
                await broadcast(
                    {
                        "type": "active_poll",
                        "poll_id": active_poll,
                        "voting_open": voting_open,
                        "question": active_question,
                    }
                )

            elif mtype == "vote":
                pid = msg.get("poll_id")
                choice = msg.get("choice")
                if not voting_open or not pid or choice not in "ABCDE":
                    continue
                if pid != active_poll:
                    continue
                if pid not in votes:
                    votes[pid] = {}
                votes[pid][choice] = votes[pid].get(choice, 0) + 1
                await broadcast(
                    {
                        "type": "results",
                        "poll_id": pid,
                        "votes": dict(votes[pid]),
                    }
                )

            elif mtype == "reset_poll":
                pid = msg.get("poll_id")
                if pid and pid in votes:
                    votes[pid] = {}
                    await broadcast({"type": "reset_poll", "poll_id": pid})

    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(ws)
