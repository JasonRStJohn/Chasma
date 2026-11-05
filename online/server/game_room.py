"""
Authoritative 60Hz GameRoom coordinator with hot-swapping ONNX AI backfill.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from fastapi import WebSocket

from chasma.ai.ai_controller import AIController
from chasma.core.simulation import ChasmaSimulation, InputState
from online.server.protocol import (
    build_state_packet,
    build_welcome_packet,
    parse_input_packet,
)


TICK_RATE = 60
TICK_INTERVAL = 1.0 / TICK_RATE
GAME_OVER_DELAY_SEC = 5.0
EMPTY_ROOM_GRACE_SEC = 30.0


@dataclass
class ConnectedClient:
    """Represents a connected WebSocket player or spectator."""
    websocket: WebSocket
    slot: int  # 0..3 for active players, -1 for spectator
    name: str = ""
    last_seq: int = 0
    latest_input: InputState = field(default_factory=InputState)
    pending_fire: bool = False  # Captures rising-edge fire presses between ticks


class GameRoom:
    """
    Manages a 4-player Chasma arena session at 60Hz.
    Unoccupied slots (0..3) are dynamically piloted by the shared ONNX AIController.
    """

    def __init__(self, room_code: str, ai_controller: AIController):
        self.room_code = room_code.upper()
        self.ai_controller = ai_controller
        self.sim = ChasmaSimulation(
            num_human_players=0,
            ai_controller=self.ai_controller,
        )

        # 4 player slots (0..3) + spectator list
        self.slots: List[Optional[ConnectedClient]] = [None, None, None, None]
        self.spectators: List[ConnectedClient] = []

        self.phase: str = "playing"  # "playing" | "game_over"
        self.game_over_until: float = 0.0
        self.last_human_time: float = time.perf_counter()
        self._loop_task: Optional[asyncio.Task] = None
        self._running: bool = False

    @property
    def human_count(self) -> int:
        return sum(1 for c in self.slots if c is not None) + len(self.spectators)

    def start_loop(self):
        """Start the background 60Hz room simulation task if not already running."""
        if self._loop_task is None or self._loop_task.done():
            self._running = True
            self._loop_task = asyncio.create_task(self._run_loop())

    def stop_loop(self):
        self._running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()

    async def connect_client(self, websocket: WebSocket, requested_name: Optional[str] = None) -> ConnectedClient:
        """Accept a WebSocket connection, assign lowest available slot (or spectator), and send welcome."""
        await websocket.accept()

        assigned_slot = -1
        for i in range(4):
            if self.slots[i] is None:
                assigned_slot = i
                break

        default_name = requested_name.strip()[:12] if requested_name and requested_name.strip() else (
            f"P{assigned_slot + 1}" if assigned_slot >= 0 else "SPEC"
        )
        client = ConnectedClient(
            websocket=websocket,
            slot=assigned_slot,
            name=default_name,
        )

        if assigned_slot >= 0:
            self.slots[assigned_slot] = client
            ship = self.sim.players[assigned_slot]
            ship.is_ai = False
            ship.name = default_name
            # If the AI ship was already eliminated before this human joined, give them a fresh ship
            if ship.lives <= 0:
                from chasma.config.settings import PLAYER_LIVES, PLAYER_SPAWNS
                ship.lives = PLAYER_LIVES
                spawn_x, spawn_y = PLAYER_SPAWNS[assigned_slot]
                ship.respawn(spawn_x, spawn_y)
                ship.alive = True
        else:
            self.spectators.append(client)

        self.last_human_time = time.perf_counter()
        await websocket.send_text(build_welcome_packet(self.room_code, assigned_slot))
        await self.broadcast_snapshot([], 0.0)
        self.start_loop()
        return client

    def disconnect_client(self, client: ConnectedClient):
        """Remove a client and immediately hand their slot back to the ONNX AI pilot."""
        if 0 <= client.slot < 4 and self.slots[client.slot] is client:
            self.slots[client.slot] = None
            ship = self.sim.players[client.slot]
            ship.is_ai = True
            ship.name = f"P{client.slot + 1} [AI]"
        elif client in self.spectators:
            self.spectators.remove(client)

        if self.human_count > 0:
            self.last_human_time = time.perf_counter()

    def handle_message(self, client: ConnectedClient, raw_text: str) -> Optional[str]:
        """
        Process an incoming JSON message from `client`.
        Returns an optional immediate response string (e.g. for `pong`).
        """
        try:
            data = json.loads(raw_text)
        except Exception:
            return None

        msg_type = data.get("t")
        if msg_type == "i" and 0 <= client.slot < 4:
            seq, input_state = parse_input_packet(data)
            client.last_seq = seq
            client.latest_input = input_state
            if input_state.fire:
                client.pending_fire = True
        elif msg_type == "cmd":
            action = data.get("action")
            if action == "set_name" and 0 <= client.slot < 4:
                raw_name = str(data.get("name", "")).strip()[:12]
                if raw_name:
                    client.name = raw_name
                    self.sim.players[client.slot].name = raw_name
            elif action == "reset_match":
                self.reset_match()
            elif action == "ping":
                return json.dumps({"t": "pong", "ts": data.get("ts", 0)}, separators=(",", ":"))
        return None

    def reset_match(self):
        """Reset all 4 ships to 3 lives and corner spawns while preserving human/AI slot assignments."""
        self.sim.reset(num_human_players=None)
        for i in range(4):
            client = self.slots[i]
            if client is not None:
                self.sim.players[i].is_ai = False
                self.sim.players[i].name = client.name
                client.pending_fire = False
            else:
                self.sim.players[i].is_ai = True
                self.sim.players[i].name = f"P{i + 1} [AI]"
        self.phase = "playing"
        self.game_over_until = 0.0

    def step_once(self) -> tuple[List[str], float]:
        """Advance the room state by 1 tick (1/60s)."""
        now = time.perf_counter()

        if self.phase == "game_over":
            remaining = max(0.0, self.game_over_until - now)
            if remaining <= 0.0:
                self.reset_match()
            return [], remaining

        # Gather latest inputs for all human slots
        input_map: Dict[int, InputState] = {}
        for i, client in enumerate(self.slots):
            if client is not None:
                fire_now = client.latest_input.fire or client.pending_fire
                client.pending_fire = False
                input_map[i] = InputState(
                    rotation=client.latest_input.rotation,
                    thrust=client.latest_input.thrust,
                    fire=fire_now,
                )

        res = self.sim.step(input_map)
        if res.is_game_over:
            self.phase = "game_over"
            self.game_over_until = now + GAME_OVER_DELAY_SEC
            return res.events, GAME_OVER_DELAY_SEC

        return res.events, 0.0

    async def broadcast_snapshot(self, events: List[str], countdown: float):
        """Send the current world state to all connected players and spectators."""
        base_packet = build_state_packet(
            sim=self.sim,
            phase=self.phase,
            ack_seq=0,
            events=events,
            countdown_remaining=countdown,
        )

        all_clients: List[ConnectedClient] = [
            c for c in self.slots if c is not None
        ] + list(self.spectators)

        for client in all_clients:
            base_packet["ack"] = client.last_seq
            payload = json.dumps(base_packet, separators=(",", ":"))
            try:
                await client.websocket.send_text(payload)
            except Exception:
                # Disconnection will be cleaned up by the WebSocket endpoint handler
                pass

    async def _run_loop(self):
        """Drift-free 60Hz authoritative room loop."""
        next_tick = time.perf_counter()
        try:
            while self._running:
                now = time.perf_counter()
                if self.human_count > 0:
                    self.last_human_time = now
                elif now - self.last_human_time > EMPTY_ROOM_GRACE_SEC:
                    self._running = False
                    break

                if now >= next_tick:
                    events, countdown = self.step_once()
                    if self.human_count > 0:
                        await self.broadcast_snapshot(events, countdown)
                    next_tick += TICK_INTERVAL
                    if now - next_tick > 0.1:
                        next_tick = now

                sleep_for = max(0.0, next_tick - time.perf_counter() - 0.001)
                await asyncio.sleep(sleep_for)
        except asyncio.CancelledError:
            pass
