"""
Desktop-to-Online Configuration & Tuning Sync Pipeline.

Reads the authoritative desktop configuration from:
- chasma/config/settings.py
- chasma/config/tuning.py (including tuning.overrides.json)
- chasma/config/colors.py
- chasma/config/controls.py

And generates:
- online/web/src/config/generated_config.ts

Can also be imported by `online/server/` via `get_runtime_config()` to send
live-tuned values in the WebSocket `welcome` handshake.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root is on sys.path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from chasma.config import settings, tuning, controls
from chasma.config.colors import ChasmaColors


def _rgb_tuple(color_val) -> list[int]:
    """Normalize an Arcade Color or tuple to a 3-element [R, G, B] list."""
    return [int(color_val[0]), int(color_val[1]), int(color_val[2])]


def get_runtime_config() -> Dict[str, Any]:
    """
    Return the complete active configuration dictionary (including any live
    overrides from tuning.overrides.json).
    """
    tuning._load()
    return {
        "screen": {
            "SCREEN_WIDTH": settings.SCREEN_WIDTH,
            "SCREEN_HEIGHT": settings.SCREEN_HEIGHT,
            "SCREEN_TITLE": settings.SCREEN_TITLE,
        },
        "arena": {
            "ARENA_MARGIN_X": settings.ARENA_MARGIN_X,
            "ARENA_MARGIN_Y": settings.ARENA_MARGIN_Y,
            "ARENA_LEFT": settings.ARENA_LEFT,
            "ARENA_RIGHT": settings.ARENA_RIGHT,
            "ARENA_BOTTOM": settings.ARENA_BOTTOM,
            "ARENA_TOP": settings.ARENA_TOP,
            "GRID_SPACING": settings.GRID_SPACING,
            "WALL_THICKNESS": settings.WALL_THICKNESS,
            "GRID_WARP_SEGMENTS": settings.GRID_WARP_SEGMENTS,
        },
        "physics": {
            "ROTATION_SPEED": settings.ROTATION_SPEED,
            "THRUST_FORCE": settings.THRUST_FORCE,
            "DRAG_COEFFICIENT": settings.DRAG_COEFFICIENT,
            "HOLLOWSTAR_SPEED": settings.HOLLOWSTAR_SPEED,
            "HOLLOWSTAR_WANDER_STRENGTH": settings.HOLLOWSTAR_WANDER_STRENGTH,
            "HOLLOWSTAR_SPIN_SPEED": settings.HOLLOWSTAR_SPIN_SPEED,
            "HOLLOWSTAR_CENTER_PULL": settings.HOLLOWSTAR_CENTER_PULL,
            "RESPAWN_DELAY": settings.RESPAWN_DELAY,
            "PLAYER_LIVES": settings.PLAYER_LIVES,
            "PLAYER_SPAWNS": [list(s) for s in settings.PLAYER_SPAWNS],
            "BLASTER_SPEED": settings.BLASTER_SPEED,
            "BLASTER_LENGTH": settings.BLASTER_LENGTH,
            "BLASTER_WIDTH": settings.BLASTER_WIDTH,
            "BLASTER_LIFETIME": settings.BLASTER_LIFETIME,
            "BLASTER_KNOCKBACK": settings.BLASTER_KNOCKBACK,
            "BLASTER_COOLDOWN": settings.BLASTER_COOLDOWN,
            "BLASTER_HIT_RADIUS": settings.BLASTER_HIT_RADIUS,
        },
        "visual": {
            "HOLLOWSTAR_DISC_OUTER": settings.HOLLOWSTAR_DISC_OUTER,
            "HOLLOWSTAR_DISC_INNER": settings.HOLLOWSTAR_DISC_INNER,
            "HOLLOWSTAR_GLOW_RADIUS": settings.HOLLOWSTAR_GLOW_RADIUS,
            "HOLLOWSTAR_SINGULARITY": settings.HOLLOWSTAR_SINGULARITY,
            "FLAME_MIN_LENGTH": settings.FLAME_MIN_LENGTH,
            "FLAME_MAX_LENGTH": settings.FLAME_MAX_LENGTH,
            "FLAME_WIDTH": settings.FLAME_WIDTH,
        },
        "controls": {
            "STICK_DEADZONE": controls.STICK_DEADZONE,
            "TRIGGER_DEADZONE": controls.TRIGGER_DEADZONE,
        },
        "tuning": {
            name: getattr(tuning, name)
            for name in tuning.tuneable_names()
        },
        "colors": {
            "GRID_BLUE": _rgb_tuple(ChasmaColors.GRID_BLUE),
            "PLAYER1_YELLOW": _rgb_tuple(ChasmaColors.PLAYER1_YELLOW),
            "PLAYER2_RED": _rgb_tuple(ChasmaColors.PLAYER2_RED),
            "PLAYER3_BLUE": _rgb_tuple(ChasmaColors.PLAYER3_BLUE),
            "PLAYER4_GREEN": _rgb_tuple(ChasmaColors.PLAYER4_GREEN),
            "SHIP_GRAY": _rgb_tuple(ChasmaColors.SHIP_GRAY),
            "HOLLOWSTAR_DISC": _rgb_tuple(ChasmaColors.HOLLOWSTAR_DISC),
            "HOLLOWSTAR_GLOW": _rgb_tuple(ChasmaColors.HOLLOWSTAR_GLOW),
            "PLAYER_SLOTS": [
                _rgb_tuple(ChasmaColors.PLAYER1_YELLOW),
                _rgb_tuple(ChasmaColors.PLAYER2_RED),
                _rgb_tuple(ChasmaColors.PLAYER3_BLUE),
                _rgb_tuple(ChasmaColors.PLAYER4_GREEN),
            ],
        },
    }


def generate_typescript_config(output_path: Path | None = None) -> Path:
    """Write `online/web/src/config/generated_config.ts` from current Python config."""
    if output_path is None:
        output_path = ROOT_DIR / "online" / "web" / "src" / "config" / "generated_config.ts"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = get_runtime_config()
    json_payload = json.dumps(cfg, indent=2)

    ts_content = f"""// AUTO-GENERATED FILE — DO NOT EDIT MANUALLY
// Generated by `python online/scripts/sync_online.py` from `chasma/config/` and `tuning.overrides.json`.

export const CHASMA_CONFIG = {json_payload} as const;

export type ChasmaConfig = typeof CHASMA_CONFIG;
export type TuningConfig = {{
  -readonly [K in keyof typeof CHASMA_CONFIG.tuning]: number;
}};
"""
    output_path.write_text(ts_content, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    out = generate_typescript_config()
    print(f"[sync_online] Synced desktop config & tuning -> {out.relative_to(ROOT_DIR)}")
