"""
Wire protocol serialization and parsing for Chasma Online.
Matches Spec 02 (`planning/specs/02-architecture-and-protocol-spec.md`).
"""

import json
from typing import Any, Dict, List, Optional

from chasma.core.simulation import ChasmaSimulation, InputState
from online.scripts.sync_online import get_runtime_config


def build_welcome_packet(room_code: str, slot: int) -> str:
    """
    Build the initial `welcome` packet sent when a client joins a room.
    Includes the complete active desktop configuration & live tuning overrides.
    """
    cfg = get_runtime_config()
    payload = {
        "t": "welcome",
        "room": room_code,
        "slot": slot,
        "config": cfg,
        "tuning": cfg["tuning"],
    }
    return json.dumps(payload, separators=(",", ":"))


def build_state_packet(
    sim: ChasmaSimulation,
    phase: str,
    ack_seq: int,
    events: List[str],
    countdown_remaining: float = 0.0,
) -> Dict[str, Any]:
    """
    Build the compact state snapshot dictionary for 60Hz broadcast.
    `ack_seq` can be customized per client before JSON encoding, or passed in a map.
    """
    hs = sim.hollowstar
    hs_tuple = [
        round(hs.center_x, 1),
        round(hs.center_y, 1),
        round(hs.spin_angle, 1),
    ] if hs else [960.0, 540.0, 0.0]

    players_tuples = []
    for p in sim.players:
        players_tuples.append([
            p.slot,
            round(p.center_x, 1),
            round(p.center_y, 1),
            round(p.velocity_x, 2),
            round(p.velocity_y, 2),
            round(p.angle % 360.0, 1),
            round(p.thrust, 3),
            p.lives,
            1 if p.alive else 0,
            1 if p.spiraling else 0,
            1 if p.is_ai else 0,
            p.name,
        ])

    proj_tuples = []
    for proj in sim.projectiles:
        proj_tuples.append([
            proj.id,
            proj.owner_slot,
            round(proj.center_x, 1),
            round(proj.center_y, 1),
            round(proj.angle % 360.0, 1),
        ])

    winner_slot: Optional[int] = sim.winner.slot if sim.winner is not None else None

    return {
        "t": "s",
        "tick": sim.tick,
        "ack": ack_seq,
        "phase": phase,
        "cd": round(countdown_remaining, 1) if countdown_remaining > 0 else 0,
        "winner": winner_slot,
        "hs": hs_tuple,
        "p": players_tuples,
        "proj": proj_tuples,
        "ev": events,
    }


def parse_input_packet(data: Dict[str, Any]) -> tuple[int, InputState]:
    """
    Parse a client `{"t": "i", "seq": 123, "rot": -1.0, "thr": 1.0, "fire": 1}` packet.
    Clamps values to prevent malformed or cheated inputs.
    """
    seq = int(data.get("seq", 0))
    rot = max(-1.0, min(1.0, float(data.get("rot", 0.0))))
    thr = max(0.0, min(1.0, float(data.get("thr", 0.0))))
    fire = bool(data.get("fire", 0))
    return seq, InputState(rotation=rot, thrust=thr, fire=fire)
