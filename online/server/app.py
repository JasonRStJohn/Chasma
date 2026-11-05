"""
FastAPI Authoritative Multiplayer Server + Static Web Host for Chasma Online.

Run locally from repo root:
    uvicorn online.server.app:app --reload --port 8080
"""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from online.scripts.sync_online import get_runtime_config
from online.server.room_manager import RoomManager


app = FastAPI(title="Chasma Online Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

room_manager = RoomManager()

WEB_DIST_DIR = Path(__file__).resolve().parents[1] / "web" / "dist"


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "active_rooms": len(room_manager.rooms),
        "onnx_loaded": room_manager.ai_controller.session is not None,
    }


@app.get("/api/config")
async def get_config():
    """Return active desktop settings and live tuning overrides."""
    return get_runtime_config()


@app.post("/api/rooms")
async def create_room():
    """Allocate a new 4-character room code for 'Create Room' / 'Quick Play'."""
    room = room_manager.create_new_room()
    return {
        "room": room.room_code,
        "human_count": room.human_count,
    }


@app.get("/api/rooms/{room_code}")
async def get_room_info(room_code: str):
    """Inspect room status before or during connection."""
    code = room_code.upper().strip()
    room = room_manager.rooms.get(code)
    if not room:
        return {"room": code, "exists": False, "human_count": 0}
    return {
        "room": room.room_code,
        "exists": True,
        "human_count": room.human_count,
        "phase": room.phase,
    }


@app.websocket("/ws/{room_code}")
async def websocket_room_endpoint(
    websocket: WebSocket,
    room_code: str,
    name: Optional[str] = Query(default=None),
):
    room = room_manager.get_or_create_room(room_code)
    client = await room.connect_client(websocket, requested_name=name)
    try:
        while True:
            raw_text = await websocket.receive_text()
            immediate_reply = room.handle_message(client, raw_text)
            if immediate_reply:
                await websocket.send_text(immediate_reply)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        room.disconnect_client(client)


# Mount compiled Vue/TS frontend if `online/web/dist` exists
if WEB_DIST_DIR.exists():
    assets_dir = WEB_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        candidate = WEB_DIST_DIR / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(WEB_DIST_DIR / "index.html"))
