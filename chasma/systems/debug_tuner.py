"""
F1-toggled debug overlay for live-tuning Hollowstar physics.

Keys (when overlay is active):
  F1        toggle overlay on/off
  [  ]      previous / next parameter
  -  =      small decrement / increment
  _  +      big decrement / increment (shift + -/=)
  F2        reset selected parameter to default
  F3        print all current values to the console
  F4        delete overrides file (revert everything to defaults)

Visual rings when active:
  cyan       outer gravity radius
  red        inner capture radius (spiral trigger)
  faint cyan sub-rings where the inverse-square pull is 2x / 4x / 8x
             (at outer / sqrt(k))
"""

import math
import arcade

from chasma.config import tuning
from chasma.config.settings import SCREEN_HEIGHT

# (param_name, small_step, big_step)
_PARAMS = [
    ("GRAVITY_STRENGTH",        100,   500),
    ("GRAVITY_OUTER_RADIUS",     10,    40),
    ("GRAVITY_INNER_RADIUS",      2,    10),
    ("GRAVITY_MIN_DIST",          1,     5),
    ("SPIRAL_DURATION",           2,    10),
    ("SPIRAL_FORCE_MULTIPLIER",   0.2,   1.0),
    ("SPIRAL_SPIN_SPEED",         0.5,   2),
    ("MAX_SPIRAL_SPEED",          0.2,   1.0),
    ("GRID_WARP_STRENGTH",       50,   200),
    ("GRID_WARP_FALLOFF",         2,    10),
]

_MONO = ("Consolas", "Courier New", "monospace")


class DebugTuner:
    def __init__(self):
        self.active = False
        self.selected = 0
        self._title = None
        self._hud_texts = None

    def toggle(self):
        self.active = not self.active

    def _select(self, delta):
        self.selected = (self.selected + delta) % len(_PARAMS)

    def _adjust(self, step_sign, big):
        name, small, big_step = _PARAMS[self.selected]
        step = big_step if big else small
        current = getattr(tuning, name)
        new_value = current + step_sign * step
        if isinstance(tuning.get_default(name), int):
            new_value = int(round(new_value))
        else:
            new_value = round(new_value, 4)
        if new_value < 0:
            new_value = 0
        tuning.set_value(name, new_value)

    def reset_selected(self):
        name, _, _ = _PARAMS[self.selected]
        tuning.reset(name)

    def on_key_press(self, key, modifiers):
        """Return True if the tuner consumed the key, False to let it fall through."""
        if key == arcade.key.F1:
            self.toggle()
            return True
        if not self.active:
            return False
        if key == arcade.key.F2:
            self.reset_selected()
            return True
        if key == arcade.key.F3:
            tuning.print_values()
            return True
        if key == arcade.key.F4:
            tuning.delete_overrides()
            return True
        if key == arcade.key.BRACKETLEFT:
            self._select(-1)
            return True
        if key == arcade.key.BRACKETRIGHT:
            self._select(1)
            return True
        shift = bool(modifiers & arcade.key.MOD_SHIFT)
        if key == arcade.key.MINUS:
            self._adjust(-1, shift)
            return True
        if key == arcade.key.EQUAL:
            self._adjust(1, shift)
            return True
        return False

    def draw_overlay(self, hollowstar_x, hollowstar_y):
        if not self.active:
            return
        self._draw_rings(hollowstar_x, hollowstar_y)
        self._draw_hud()

    def _draw_rings(self, hx, hy):
        outer = tuning.GRAVITY_OUTER_RADIUS
        inner = tuning.GRAVITY_INNER_RADIUS
        arcade.draw_circle_outline(hx, hy, outer, (0, 200, 220, 160), border_width=1)
        arcade.draw_circle_outline(hx, hy, inner, (230, 60, 60, 200), border_width=2)
        for k in (2, 4, 8):
            r = outer / math.sqrt(k)
            if r <= inner:
                continue
            arcade.draw_circle_outline(hx, hy, r, (0, 200, 220, 70), border_width=1)

    def _init_hud(self):
        self._title = arcade.Text(
            "DEBUG TUNER   F1 off   [ ] cycle   - = step   _ + big   F2 reset   F3 print   F4 clear",
            10, SCREEN_HEIGHT - 18,
            (180, 220, 255), font_size=11, font_name=_MONO,
        )
        self._hud_texts = []
        for i in range(len(_PARAMS)):
            self._hud_texts.append(arcade.Text(
                "", 10, SCREEN_HEIGHT - 40 - i * 22,
                (200, 200, 200), font_size=12, font_name=_MONO,
            ))

    def _draw_hud(self):
        if self._hud_texts is None:
            self._init_hud()

        self._title.draw()
        for i, (name, _, _) in enumerate(_PARAMS):
            current = getattr(tuning, name)
            default = tuning.get_default(name)
            modified = current != default
            prefix = "> " if i == self.selected else "  "
            suffix = "" if not modified else f"   (was {default})"
            t = self._hud_texts[i]
            t.text = f"{prefix}{name:<26} = {current}{suffix}"
            if i == self.selected:
                t.color = (255, 230, 120)
            elif modified:
                t.color = (180, 255, 180)
            else:
                t.color = (200, 200, 200)
            t.draw()
