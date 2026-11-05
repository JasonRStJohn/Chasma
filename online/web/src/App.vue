<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { CHASMA_CONFIG } from "./config/generated_config";
import { WebInputManager } from "./game/input";
import { RenderPlayer, WorldStatePredictor } from "./game/prediction";
import { ArenaRenderer } from "./game/renderer";
import { WebSoundManager } from "./game/sound";
import { ChasmaSocketClient } from "./network/socket";

const canvasRef = ref<HTMLCanvasElement | null>(null);

// UI State
const inRoom = ref(false);
const roomCode = ref("");
const joinCodeInput = ref("");
const callsign = ref(localStorage.getItem("chasma_callsign") || "");
const urlInviteRoom = ref<string | null>(null);
const mySlot = ref(-1);
const soundEnabled = ref(true);
const showDebug = ref(false);
const pingMs = ref(0);
const linkCopied = ref(false);
const matchPhase = ref("playing");
const matchCountdown = ref(0);
const matchWinnerSlot = ref<number | null>(null);

// HUD Players list
const hudPlayers = ref<RenderPlayer[]>([]);

const sound = new WebSoundManager();
soundEnabled.value = sound.enabled;

const predictor = new WorldStatePredictor();
const renderer = new ArenaRenderer();

let inputManager: WebInputManager | null = null;
let socketClient: ChasmaSocketClient | null = null;
let animFrameId: number | null = null;
let lastInputSendTime = 0;

const SLOT_HEX_COLORS = ["#ffff00", "#ff3b3b", "#3b82f6", "#22c55e"];
const SLOT_NAMES = ["YELLOW", "RED", "BLUE", "GREEN"];

function saveCallsign(): void {
  localStorage.setItem("chasma_callsign", callsign.value.trim().slice(0, 12));
}

function updateUrlParam(code: string | null): void {
  const url = new URL(window.location.href);
  if (code) {
    url.searchParams.set("room", code.toUpperCase());
  } else {
    url.searchParams.delete("room");
  }
  window.history.replaceState({}, "", url.toString());
}

async function createAndJoinRoom(copyLink = true): Promise<void> {
  sound.unlock();
  sound.play("menu_select");
  saveCallsign();

  let code = "";
  try {
    const res = await fetch("/api/rooms", { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      code = data.room;
    }
  } catch {
    // Fallback client-side code if offline
  }
  if (!code) {
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    code = Array.from({ length: 4 }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
  }

  connectToRoom(code);
  if (copyLink) {
    await copyInviteLink(code);
  }
}

function joinRoomByCode(codeToJoin?: string): void {
  const target = (codeToJoin ?? joinCodeInput.value).trim().toUpperCase();
  if (!target) return;
  sound.unlock();
  sound.play("menu_select");
  saveCallsign();
  connectToRoom(target);
}

function connectToRoom(code: string): void {
  const cleanCode = code.trim().toUpperCase();
  roomCode.value = cleanCode;
  urlInviteRoom.value = null;
  updateUrlParam(cleanCode);
  inRoom.value = true;

  socketClient?.connect(cleanCode, callsign.value);
}

function leaveRoom(): void {
  sound.play("menu_select");
  socketClient?.disconnect();
  inRoom.value = false;
  roomCode.value = "";
  mySlot.value = -1;
  updateUrlParam(null);
}

async function copyInviteLink(overrideCode?: string): Promise<void> {
  const code = (overrideCode || roomCode.value).toUpperCase();
  if (!code) return;
  const inviteUrl = `${window.location.origin}${window.location.pathname}?room=${code}`;
  try {
    await navigator.clipboard.writeText(inviteUrl);
    linkCopied.value = true;
    setTimeout(() => {
      linkCopied.value = false;
    }, 2200);
  } catch {
    // Clipboard API fallback
  }
}

function triggerResetMatch(): void {
  sound.play("menu_select");
  socketClient?.sendCommand("reset_match");
}

function toggleMute(): void {
  soundEnabled.value = sound.toggleMute();
}

function toggleDebug(): void {
  showDebug.value = !showDebug.value;
}

function renderLoop(now: number): void {
  animFrameId = requestAnimationFrame(renderLoop);

  const canvas = canvasRef.value;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  // Poll inputs & send at ~60Hz when connected in a room
  if (inRoom.value && inputManager && socketClient?.connected) {
    if (now - lastInputSendTime >= 15.5) {
      lastInputSendTime = now;
      const localInput = inputManager.poll();
      const seq = predictor.recordAndPredictLocalInput(localInput);
      socketClient.sendInput(seq, localInput);
    }
    pingMs.value = socketClient.pingMs;
  }

  const world = inRoom.value ? predictor.getRenderState() : null;
  if (world) {
    hudPlayers.value = world.players;
    matchPhase.value = world.phase;
    matchCountdown.value = world.countdown;
    matchWinnerSlot.value = world.winner;
  }

  renderer.render(
    ctx,
    world,
    mySlot.value,
    predictor.tuning,
    showDebug.value,
    pingMs.value
  );
}

onMounted(() => {
  // Check if user opened a shared invite URL (`?room=ABCD`)
  const params = new URLSearchParams(window.location.search);
  const invitedRoom = params.get("room");
  if (invitedRoom && invitedRoom.trim().length > 0) {
    urlInviteRoom.value = invitedRoom.trim().toUpperCase().slice(0, 8);
    joinCodeInput.value = urlInviteRoom.value;
  }

  inputManager = new WebInputManager({
    onDebugToggle: toggleDebug,
    onMuteToggle: toggleMute,
    onActionConfirm: () => {
      if (inRoom.value && matchPhase.value === "game_over") {
        triggerResetMatch();
      }
    },
  });

  socketClient = new ChasmaSocketClient({
    onWelcome: (pkt) => {
      mySlot.value = pkt.slot;
      roomCode.value = pkt.room;
      predictor.reset(pkt.slot, pkt.tuning);
    },
    onState: (pkt) => {
      predictor.onServerSnapshot(pkt);
      if (pkt.ev && pkt.ev.length > 0) {
        for (const evName of pkt.ev) {
          sound.play(evName);
        }
      }
    },
    onDisconnect: () => {
      // Keep UI responsive on disconnect
    },
  });

  animFrameId = requestAnimationFrame(renderLoop);
});

onBeforeUnmount(() => {
  if (animFrameId !== null) cancelAnimationFrame(animFrameId);
  inputManager?.destroy();
  socketClient?.disconnect();
});
</script>

<template>
  <div class="chasma-viewport">
    <!-- Top HUD Bar when inside a room -->
    <header v-if="inRoom" class="hud-bar">
      <div class="hud-players">
        <div
          v-for="p in hudPlayers"
          :key="p.slot"
          class="player-pill"
          :class="{ 'is-me': p.slot === mySlot, 'is-out': p.lives <= 0 }"
          :style="{ borderColor: SLOT_HEX_COLORS[p.slot] }"
        >
          <span class="dot" :style="{ backgroundColor: SLOT_HEX_COLORS[p.slot] }"></span>
          <span class="p-name">
            {{ p.name }}
            <small v-if="p.slot === mySlot" class="you-tag">YOU</small>
          </span>
          <span class="p-lives" :style="{ color: SLOT_HEX_COLORS[p.slot] }">
            <template v-if="p.lives > 0">
              {{ "▲".repeat(p.lives) }}
            </template>
            <template v-else>OUT</template>
          </span>
        </div>
      </div>

      <div class="hud-actions">
        <div class="room-badge">
          <span class="room-label">ROOM</span>
          <strong class="room-code">{{ roomCode }}</strong>
        </div>

        <button class="hud-btn invite-btn" @click="copyInviteLink()">
          {{ linkCopied ? "✓ LINK COPIED!" : "🔗 COPY INVITE URL" }}
        </button>

        <button class="hud-btn" title="Restart match with 3 lives" @click="triggerResetMatch">
          ↻ RESET
        </button>

        <button class="hud-btn" @click="toggleMute">
          {{ soundEnabled ? "🔊 SFX" : "🔇 MUTE" }}
        </button>

        <button class="hud-btn" :class="{ active: showDebug }" @click="toggleDebug">
          F1 DEBUG
        </button>

        <span class="ping-badge">{{ pingMs }} ms</span>

        <button class="hud-btn leave-btn" @click="leaveRoom">✕ LEAVE</button>
      </div>
    </header>

    <!-- 16:9 Scaled 1920x1080 Vector Arena Canvas -->
    <div class="canvas-stage">
      <canvas
        ref="canvasRef"
        :width="CHASMA_CONFIG.screen.SCREEN_WIDTH"
        :height="CHASMA_CONFIG.screen.SCREEN_HEIGHT"
        class="arena-canvas"
      ></canvas>

      <!-- Landing / Lobby Modal Overlay -->
      <div v-if="!inRoom" class="overlay-backdrop">
        <div class="lobby-card">
          <div class="title-header">
            <h1 class="game-title">CHASMA</h1>
            <p class="game-subtitle">SURVIVE THE HOLLOWSTAR • 4-PLAYER ARENA COMBAT</p>
          </div>

          <div class="form-row">
            <label for="callsign-input">PILOT CALLSIGN</label>
            <input
              id="callsign-input"
              v-model="callsign"
              maxlength="12"
              placeholder="Enter Callsign (e.g. WOLF)"
              class="retro-input"
            />
          </div>

          <!-- Direct Invite URL Fast-Join Banner -->
          <div v-if="urlInviteRoom" class="invite-banner">
            <p class="invite-prompt">
              YOU WERE INVITED TO ROOM <strong>{{ urlInviteRoom }}</strong>
            </p>
            <button class="primary-btn pulse" @click="joinRoomByCode(urlInviteRoom)">
              🚀 LAUNCH INTO ROOM {{ urlInviteRoom }}
            </button>
          </div>

          <div class="action-grid">
            <button class="primary-btn" @click="createAndJoinRoom(true)">
              ⚡ CREATE ROOM &amp; COPY INVITE URL
            </button>

            <div class="join-box">
              <input
                v-model="joinCodeInput"
                maxlength="6"
                placeholder="ROOM CODE"
                class="retro-input code-input"
                @keyup.enter="joinRoomByCode()"
              />
              <button class="secondary-btn" @click="joinRoomByCode()">JOIN ROOM</button>
            </div>
          </div>

          <div class="controls-guide">
            <div>
              <strong>KEYBOARD:</strong> <code>←/→</code> or <code>A/D</code> Rotate •
              <code>↑</code> or <code>W</code> Thrust • <code>SPACE</code> Fire
            </div>
            <div>
              <strong>GAMEPAD:</strong> Left Stick Rotate • Right Trigger Thrust •
              <code>A</code> Button Fire
            </div>
            <div class="ai-note">
              Empty slots (P1–P4) are automatically flown by the server's ONNX Neural Pilot and hot-swap when friends click your link.
            </div>
          </div>
        </div>
      </div>

      <!-- Game Over Winner Banner Overlay -->
      <div v-if="inRoom && matchPhase === 'game_over'" class="overlay-backdrop game-over-backdrop">
        <div class="gameover-card">
          <template v-if="matchWinnerSlot !== null && hudPlayers[matchWinnerSlot]">
            <h2
              class="winner-title"
              :style="{ color: SLOT_HEX_COLORS[matchWinnerSlot] }"
            >
              {{ hudPlayers[matchWinnerSlot].name }} ({{ SLOT_NAMES[matchWinnerSlot] }}) WINS!
            </h2>
            <p class="winner-sub">SURVIVED THE HOLLOWSTAR</p>
          </template>
          <template v-else>
            <h2 class="winner-title">ANNIHILATION DRAW!</h2>
            <p class="winner-sub">THE HOLLOWSTAR CONSUMED ALL SHIPS</p>
          </template>

          <p class="rematch-timer">Next round in {{ matchCountdown.toFixed(0) }}s...</p>
          <button class="primary-btn" @click="triggerResetMatch">
            PLAY AGAIN NOW (SPACE / A)
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chasma-viewport {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  background: radial-gradient(circle at center, #060b18 0%, #02040a 100%);
}

.hud-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
  background: rgba(5, 10, 22, 0.92);
  border-bottom: 1px solid rgba(100, 180, 255, 0.25);
  z-index: 10;
  gap: 12px;
  flex-wrap: wrap;
}

.hud-players {
  display: flex;
  gap: 10px;
  align-items: center;
}

.player-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 12px;
  background: rgba(12, 20, 38, 0.85);
  border: 1px solid #444;
  border-radius: 4px;
  font-size: 13px;
}

.player-pill.is-me {
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.2);
  background: rgba(25, 40, 75, 0.9);
}

.player-pill.is-out {
  opacity: 0.45;
}

.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}

.p-name {
  font-weight: bold;
  color: #f0f6ff;
}

.you-tag {
  margin-left: 4px;
  padding: 1px 4px;
  font-size: 10px;
  background: #f0f6ff;
  color: #050a16;
  border-radius: 2px;
}

.p-lives {
  font-weight: bold;
  letter-spacing: 2px;
  min-width: 38px;
  text-align: right;
}

.hud-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.room-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  background: rgba(20, 45, 90, 0.6);
  border: 1px solid rgba(120, 200, 255, 0.4);
  border-radius: 4px;
}

.room-label {
  font-size: 11px;
  color: #8ab4f8;
}

.room-code {
  font-size: 15px;
  letter-spacing: 2px;
  color: #ffffff;
}

.hud-btn {
  padding: 6px 11px;
  background: rgba(20, 32, 60, 0.85);
  color: #d2e4ff;
  border: 1px solid rgba(120, 180, 255, 0.35);
  border-radius: 4px;
  font-family: inherit;
  font-size: 12px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.15s ease;
}

.hud-btn:hover {
  background: rgba(40, 70, 130, 0.9);
  border-color: #7ff0ff;
}

.hud-btn.active {
  background: rgba(0, 180, 210, 0.3);
  border-color: #00ffff;
  color: #00ffff;
}

.invite-btn {
  background: rgba(210, 140, 40, 0.25);
  border-color: #f59e0b;
  color: #fde68a;
}

.invite-btn:hover {
  background: rgba(245, 158, 11, 0.4);
}

.leave-btn {
  border-color: rgba(255, 90, 90, 0.4);
  color: #fca5a5;
}

.ping-badge {
  font-size: 12px;
  color: #7ff0ff;
  min-width: 52px;
  text-align: right;
}

.canvas-stage {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 6px;
}

.arena-canvas {
  width: 100%;
  height: 100%;
  max-width: calc((100vh - 60px) * (16 / 9));
  max-height: calc(100vw * (9 / 16));
  aspect-ratio: 16 / 9;
  background: #000;
  box-shadow: 0 0 40px rgba(0, 150, 255, 0.15);
}

.overlay-backdrop {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(2, 5, 14, 0.78);
  backdrop-filter: blur(4px);
}

.lobby-card,
.gameover-card {
  width: 540px;
  max-width: 92vw;
  padding: 32px;
  background: rgba(8, 15, 32, 0.95);
  border: 1px solid rgba(120, 200, 255, 0.45);
  box-shadow: 0 0 50px rgba(0, 120, 255, 0.25);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  text-align: center;
}

.game-title {
  font-size: 46px;
  letter-spacing: 8px;
  color: #f0f8ff;
  text-shadow: 0 0 18px rgba(100, 200, 255, 0.6);
}

.game-subtitle {
  font-size: 12px;
  letter-spacing: 2px;
  color: #f59e0b;
  margin-top: 4px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-align: left;
}

.form-row label {
  font-size: 11px;
  letter-spacing: 1.5px;
  color: #93c5fd;
}

.retro-input {
  padding: 11px 14px;
  background: rgba(3, 7, 18, 0.9);
  border: 1px solid rgba(100, 180, 255, 0.4);
  border-radius: 4px;
  color: #ffffff;
  font-family: inherit;
  font-size: 15px;
  outline: none;
}

.retro-input:focus {
  border-color: #f59e0b;
}

.invite-banner {
  padding: 16px;
  background: rgba(245, 158, 11, 0.14);
  border: 1px solid #f59e0b;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.invite-prompt {
  font-size: 14px;
  color: #fde68a;
}

.action-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.primary-btn {
  padding: 13px 18px;
  background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
  color: #ffffff;
  border: 1px solid #fbbf24;
  border-radius: 5px;
  font-family: inherit;
  font-size: 15px;
  font-weight: bold;
  letter-spacing: 1px;
  cursor: pointer;
  transition: transform 0.1s ease, filter 0.15s ease;
}

.primary-btn:hover {
  filter: brightness(1.15);
}

.join-box {
  display: flex;
  gap: 8px;
}

.code-input {
  flex: 1;
  text-transform: uppercase;
  letter-spacing: 3px;
  text-align: center;
  font-weight: bold;
}

.secondary-btn {
  padding: 11px 20px;
  background: rgba(30, 58, 138, 0.7);
  color: #e0f2fe;
  border: 1px solid #60a5fa;
  border-radius: 5px;
  font-family: inherit;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
}

.secondary-btn:hover {
  background: rgba(37, 99, 235, 0.85);
}

.controls-guide {
  margin-top: 4px;
  padding-top: 14px;
  border-top: 1px solid rgba(100, 180, 255, 0.2);
  font-size: 12px;
  color: #94a3b8;
  display: flex;
  flex-direction: column;
  gap: 6px;
  line-height: 1.4;
}

.controls-guide code {
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.08);
  padding: 1px 5px;
  border-radius: 3px;
}

.ai-note {
  color: #7dd3fc;
  font-size: 11px;
  margin-top: 4px;
}

.winner-title {
  font-size: 28px;
  letter-spacing: 2px;
}

.winner-sub {
  font-size: 13px;
  color: #cbd5e1;
  letter-spacing: 2px;
}

.rematch-timer {
  font-size: 14px;
  color: #f59e0b;
}
</style>
