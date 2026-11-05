# Multi-stage Dockerfile for Chasma Online (Multi-arch: Apple Silicon arm64 & x86_64)
# Build & run from the repository root:
#   docker compose -f online/docker-compose.yml up -d --build

# --- Stage 1: Sync Python Config & Build Vue 3 + TypeScript Web Client ---
FROM node:22-slim AS web-builder
RUN apt-get update && apt-get install -y --no-install-recommends python3 && rm -rf /var/lib/apt/lists/*
WORKDIR /build

# Copy desktop config & sync script so generated_config.ts is built from source of truth
COPY README.md tuning.overrides.json* ./
COPY chasma/ ./chasma/
COPY online/scripts/ ./online/scripts/
RUN python3 online/scripts/sync_online.py

WORKDIR /build/online/web
COPY online/web/package*.json ./
RUN npm install
COPY online/web/ ./
RUN npx vite build

# --- Stage 2: Authoritative Python 60Hz Server + Static SPA Host ---
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY online/requirements.txt ./online/requirements.txt
RUN pip install --no-cache-dir -r online/requirements.txt

# Copy shared Chasma domain kernel, config, and ONNX neural model
COPY README.md tuning.overrides.json* ./
COPY chasma/ ./chasma/

# Copy online server and compiled web frontend
COPY online/ ./online/
COPY --from=web-builder /build/online/web/dist ./online/web/dist

EXPOSE 8080

# Note: Keep --workers 1 so in-memory GameRoom state is shared across all WebSocket connections.
# --proxy-headers and --forwarded-allow-ips=* ensure clean operation behind Cloudflare Tunnel + NGINX.
CMD ["uvicorn", "online.server.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*", "--ws-ping-interval", "20", "--ws-ping-timeout", "20"]
