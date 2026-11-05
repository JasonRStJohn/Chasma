# Chasma Online ("Send Friends a URL")

This directory (`online/`) contains the browser-based multiplayer server and web client for **Chasma**, designed to co-exist alongside the desktop Arcade application (`main.py`) while sharing the exact same physics kernel (`chasma/core/simulation.py`), configuration (`chasma/config/`), live `F1` tuning overrides (`tuning.overrides.json`), and ONNX neural pilot (`chasma/ai/models/chasma_pilot.onnx`).

---

## 🏗️ Directory Structure

```text
online/
├── Dockerfile              # Multi-stage Docker build (serves Web SPA + WebSocket server on :8080)
├── requirements.txt        # FastAPI, Uvicorn, WebSockets, ONNX Runtime, NumPy
├── scripts/
│   └── sync_online.py      # Syncs desktop Python config/tuning -> online/web/src/config/generated_config.ts
├── server/
│   ├── app.py              # FastAPI HTTP + WebSocket entrypoint & static SPA mount
│   ├── room_manager.py     # Allocates 4-char room codes & manages active rooms
│   ├── game_room.py        # 60Hz authoritative room loop & hot-swap ONNX AI backfill
│   └── protocol.py         # Wire protocol serializer & input validator
└── web/                    # Vue 3 + TypeScript + HTML5 Canvas + Web Audio API client
    ├── src/
    │   ├── App.vue         # Lobby, Invite Link HUD, and Game Over overlays
    │   ├── config/
    │   │   └── generated_config.ts # Auto-generated from desktop Python settings & tuning
    │   ├── game/
    │   │   ├── renderer.ts    # 1920x1080 Canvas2D warped spacetime grid, Hollowstar & ships
    │   │   ├── prediction.ts  # Client-side prediction, reconciliation & 45ms lerp buffer
    │   │   ├── input.ts       # Keyboard + HTML5 Gamepad API polling
    │   │   └── sound.ts       # Zero-asset Web Audio API procedural waveform synthesizer
    │   └── network/
    │       └── socket.ts      # WebSocket client & RTT ping monitor
```

---

## 🔄 Desktop $\to$ Online Iteration Pipeline

1. **Test & Tune Locally on Desktop:**
   ```powershell
   python main.py
   ```
   - Use `F1` to tweak physics live (auto-saved to `tuning.overrides.json`).
   - Edit `chasma/core/simulation.py` or `chasma/config/settings.py` to iterate on gameplay rules.
   - Run `python chasma/ai/train.py` to retrain `chasma_pilot.onnx`.

2. **Sync to Online:**
   ```powershell
   python online/scripts/sync_online.py
   ```
   *(This also runs automatically on `npm run dev` / `npm run build` and inside the `Dockerfile`, and live `tuning.overrides.json` values are streamed dynamically in the WebSocket `welcome` handshake).*

---

## 🚀 Running Locally

### Option A: Single-Container Docker (Recommended for Production Parity)
From the repository root (`C:\Users\jason\GitRepos\Chasma`):
```powershell
docker build -f online/Dockerfile -t chasma-online .
docker run --rm -p 8080:8080 chasma-online
```
Then open **`http://localhost:8080`** (or share via Cloudflare Tunnel / ngrok / AWS ECS / Fly.io).

### Option B: Local Dev Server (FastAPI + Vite HMR)
1. **Start the Authoritative Python Server (Terminal 1, from repo root):**
   ```powershell
   python -m uvicorn online.server.app:app --reload --port 8080
   ```
2. **Start the Vite Frontend (Terminal 2, from `online/web`):**
   ```powershell
   cd online/web
   npm install
   npm run dev
   ```
   Open **`http://localhost:5173`**, click **Create Room & Copy Invite URL**, and open the copied `?room=ABCD` link in a second browser tab!
