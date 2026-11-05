"""
Multi-room coordinator for Chasma Online.
Allocates 4-character unambiguous room codes and shares a single ONNX AIController across rooms.
"""

import random
import time
from typing import Dict, Optional

from chasma.ai.ai_controller import AIController
from online.server.game_room import EMPTY_ROOM_GRACE_SEC, GameRoom


# Exclude ambiguous characters (0, O, 1, I)
ROOM_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
MAX_ACTIVE_ROOMS = 50


class RoomManager:
    """Manages active GameRoom instances and room code allocation."""

    def __init__(self):
        self.ai_controller = AIController()
        self.rooms: Dict[str, GameRoom] = {}

    def _cleanup_stale_rooms(self):
        now = time.perf_counter()
        stale_codes = [
            code
            for code, room in self.rooms.items()
            if room.human_count == 0 and (now - room.last_human_time) > EMPTY_ROOM_GRACE_SEC
        ]
        for code in stale_codes:
            room = self.rooms.pop(code, None)
            if room:
                room.stop_loop()

    def generate_room_code(self, length: int = 4) -> str:
        """Generate an unused 4-character room code."""
        self._cleanup_stale_rooms()
        for _ in range(100):
            code = "".join(random.choices(ROOM_CODE_ALPHABET, k=length))
            if code not in self.rooms:
                return code
        return "".join(random.choices(ROOM_CODE_ALPHABET, k=length + 1))

    def get_or_create_room(self, room_code: str) -> GameRoom:
        """Fetch an existing room by code or create a new one."""
        self._cleanup_stale_rooms()
        clean_code = "".join(ch for ch in room_code.upper() if ch.isalnum())[:8]
        if not clean_code:
            clean_code = self.generate_room_code()

        if clean_code not in self.rooms:
            if len(self.rooms) >= MAX_ACTIVE_ROOMS:
                # Evict oldest empty room if at capacity
                for code, r in list(self.rooms.items()):
                    if r.human_count == 0:
                        r.stop_loop()
                        del self.rooms[code]
                        break
            self.rooms[clean_code] = GameRoom(clean_code, self.ai_controller)

        return self.rooms[clean_code]

    def create_new_room(self) -> GameRoom:
        """Create and register a brand-new room with a fresh 4-char code."""
        code = self.generate_room_code()
        return self.get_or_create_room(code)
