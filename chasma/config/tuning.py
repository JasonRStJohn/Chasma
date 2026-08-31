"""
Live-tunable values for Hollowstar physics.

Values start from settings.py defaults and are overlaid with any values
present in tuning.overrides.json. The debug tuner calls set_value() to
update a value and persist it to disk, so tweaks survive restarts.

Access values as module attributes, e.g. `tuning.GRAVITY_STRENGTH`. Don't
do `from tuning import *` — that captures the value at import time and
won't see later adjustments.
"""

import json
from pathlib import Path

from chasma.config import settings

_TUNEABLE = [
    "GRAVITY_STRENGTH",
    "GRAVITY_OUTER_RADIUS",
    "GRAVITY_INNER_RADIUS",
    "GRAVITY_MIN_DIST",
    "SPIRAL_DURATION",
    "SPIRAL_FORCE_MULTIPLIER",
    "SPIRAL_SPIN_SPEED",
    "MAX_SPIRAL_SPEED",
    "GRID_WARP_STRENGTH",
    "GRID_WARP_FALLOFF",
]

_DEFAULTS = {name: getattr(settings, name) for name in _TUNEABLE}

# tuning.py → chasma/config/ → chasma/ → project root
_OVERRIDES_PATH = Path(__file__).resolve().parents[2] / "tuning.overrides.json"


def _load():
    for name, value in _DEFAULTS.items():
        globals()[name] = value
    if not _OVERRIDES_PATH.exists():
        return
    try:
        with open(_OVERRIDES_PATH, "r") as f:
            overrides = json.load(f)
        for name, value in overrides.items():
            if name in _DEFAULTS:
                globals()[name] = value
    except Exception as e:
        print(f"[tuning] failed to load overrides: {e}")


def _save_overrides():
    overrides = {
        name: globals()[name]
        for name in _TUNEABLE
        if globals()[name] != _DEFAULTS[name]
    }
    try:
        if overrides:
            with open(_OVERRIDES_PATH, "w") as f:
                json.dump(overrides, f, indent=2)
        elif _OVERRIDES_PATH.exists():
            _OVERRIDES_PATH.unlink()
    except Exception as e:
        print(f"[tuning] failed to save overrides: {e}")


def set_value(name, value):
    if name not in _DEFAULTS:
        raise KeyError(name)
    globals()[name] = value
    _save_overrides()


def reset(name):
    if name not in _DEFAULTS:
        raise KeyError(name)
    globals()[name] = _DEFAULTS[name]
    _save_overrides()


def get_default(name):
    return _DEFAULTS[name]


def tuneable_names():
    return list(_TUNEABLE)


def delete_overrides():
    for name in _TUNEABLE:
        globals()[name] = _DEFAULTS[name]
    try:
        if _OVERRIDES_PATH.exists():
            _OVERRIDES_PATH.unlink()
    except Exception as e:
        print(f"[tuning] failed to delete overrides: {e}")


def print_values():
    print("[tuning] current values:")
    for name in _TUNEABLE:
        cur = globals()[name]
        default = _DEFAULTS[name]
        marker = "" if cur == default else f"  (default: {default})"
        print(f"  {name:<26} = {cur}{marker}")
    if _OVERRIDES_PATH.exists():
        print(f"[tuning] overrides file: {_OVERRIDES_PATH}")
    else:
        print("[tuning] no overrides file (all defaults)")


_load()
