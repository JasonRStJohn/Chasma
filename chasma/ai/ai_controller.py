import os
import math
from pathlib import Path
import numpy as np

try:
    import onnxruntime as ort
except ImportError:
    ort = None

from chasma.config.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    ARENA_LEFT,
    ARENA_RIGHT,
    ARENA_BOTTOM,
    ARENA_TOP,
    ROTATION_SPEED,
    THRUST_FORCE,
    BLASTER_SPEED,
)
from chasma.config import tuning
from chasma.systems.input_manager import InputState


# Default model path in chasma/ai/models/chasma_pilot.onnx
DEFAULT_MODEL_PATH = Path(__file__).parent / "models" / "chasma_pilot.onnx"


class AIController:
    """
    Evaluates game telemetry (ship state, opponents, Hollowstar, arena walls)
    and produces an InputState for an AI player slot every frame.
    Supports ONNX Runtime neural inference with an algorithmic fallback.
    """

    def __init__(self, model_path=None):
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        self.session = None
        self.input_name = None
        self.max_speed = 10.0
        self.screen_diag = math.hypot(SCREEN_WIDTH, SCREEN_HEIGHT)

        if ort and self.model_path.exists():
            try:
                self.session = ort.InferenceSession(str(self.model_path))
                self.input_name = self.session.get_inputs()[0].name
                print(f"[AIController] Loaded ONNX neural model: {self.model_path.name}")
            except Exception as e:
                print(f"[AIController] Failed to load ONNX model ({e}), using heuristic pilot.")
        else:
            print("[AIController] No ONNX model found. Using combat heuristic pilot.")

    def get_input_state(self, bot_player, all_players, hollowstar) -> InputState:
        """
        Generate InputState for bot_player.
        """
        if not bot_player.alive or bot_player.spiraling:
            return InputState()

        # Find closest living target opponent
        target = self._find_target(bot_player, all_players)

        if self.session is not None:
            return self._predict_onnx(bot_player, target, hollowstar)
        else:
            return self._predict_heuristic(bot_player, target, hollowstar)

    def _find_target(self, bot_player, all_players):
        """Find the nearest active, non-spiraling opponent."""
        closest_target = None
        min_dist = float("inf")

        for other in all_players:
            if other is bot_player or not other.alive or other.spiraling:
                continue
            dist = math.hypot(other.center_x - bot_player.center_x, other.center_y - bot_player.center_y)
            if dist < min_dist:
                min_dist = dist
                closest_target = other

        return closest_target

    def _build_observation(self, bot, target, hollowstar) -> np.ndarray:
        """
        Constructs normalized 14-float observation vector:
        [self_vx, self_vy, sin_angle, cos_angle,
         rel_target_x, rel_target_y, target_dist, rel_target_vx, rel_target_vy, heading_alignment,
         rel_hs_x, rel_hs_y, hs_dist, in_gravity_zone]
        """
        rad = math.radians(bot.angle)
        heading_x = math.sin(rad)
        heading_y = math.cos(rad)

        norm_vx = float(np.clip(bot.velocity_x / self.max_speed, -1.0, 1.0))
        norm_vy = float(np.clip(bot.velocity_y / self.max_speed, -1.0, 1.0))

        # Target telemetry
        if target and target.alive:
            dx_t = target.center_x - bot.center_x
            dy_t = target.center_y - bot.center_y
            dist_t = math.hypot(dx_t, dy_t)
            norm_dx_t = float(np.clip(dx_t / SCREEN_WIDTH, -1.0, 1.0))
            norm_dy_t = float(np.clip(dy_t / SCREEN_HEIGHT, -1.0, 1.0))
            norm_dist_t = float(np.clip(dist_t / self.screen_diag, 0.0, 1.0))

            rel_vx = float(np.clip((target.velocity_x - bot.velocity_x) / self.max_speed, -1.0, 1.0))
            rel_vy = float(np.clip((target.velocity_y - bot.velocity_y) / self.max_speed, -1.0, 1.0))

            alignment = (heading_x * (dx_t / max(dist_t, 1))) + (heading_y * (dy_t / max(dist_t, 1)))
        else:
            norm_dx_t, norm_dy_t, norm_dist_t = 0.0, 0.0, 1.0
            rel_vx, rel_vy = 0.0, 0.0
            alignment = 1.0

        # Hollowstar telemetry
        if hollowstar:
            dx_hs = hollowstar.center_x - bot.center_x
            dy_hs = hollowstar.center_y - bot.center_y
            dist_hs = math.hypot(dx_hs, dy_hs)
            norm_dx_hs = float(np.clip(dx_hs / SCREEN_WIDTH, -1.0, 1.0))
            norm_dy_hs = float(np.clip(dy_hs / SCREEN_HEIGHT, -1.0, 1.0))
            norm_dist_hs = float(np.clip(dist_hs / self.screen_diag, 0.0, 1.0))
            in_gravity = 1.0 if dist_hs < tuning.GRAVITY_OUTER_RADIUS else 0.0
        else:
            norm_dx_hs, norm_dy_hs, norm_dist_hs, in_gravity = 0.0, 0.0, 1.0, 0.0

        return np.array(
            [[
                norm_vx,
                norm_vy,
                heading_x,
                heading_y,
                norm_dx_t,
                norm_dy_t,
                norm_dist_t,
                rel_vx,
                rel_vy,
                alignment,
                norm_dx_hs,
                norm_dy_hs,
                norm_dist_hs,
                in_gravity,
            ]],
            dtype=np.float32,
        )

    def _predict_onnx(self, bot, target, hollowstar) -> InputState:
        """Run ONNX inference."""
        obs = self._build_observation(bot, target, hollowstar)
        outputs = self.session.run(None, {self.input_name: obs})
        actions = outputs[0][0]  # [steering, thrust, fire]

        state = InputState()
        steering = int(actions[0])
        thrust = int(actions[1])

        if steering == 1:
            state.rotation = -1.0
        elif steering == 2:
            state.rotation = 1.0

        state.thrust = 1.0 if thrust == 1 else 0.0

        if len(actions) > 2:
            state.fire = bool(actions[2] == 1)
        elif target:
            # Auto-fire if pointing at target within range
            dx = target.center_x - bot.center_x
            dy = target.center_y - bot.center_y
            dist = math.hypot(dx, dy)
            rad = math.radians(bot.angle)
            alignment = (math.sin(rad) * (dx / max(dist, 1))) + (math.cos(rad) * (dy / max(dist, 1)))
            state.fire = bool(dist < 500 and alignment > 0.92)

        return state

    def _predict_heuristic(self, bot, target, hollowstar) -> InputState:
        """
        Combat heuristic pilot:
        1. Gravity avoidance: Evade Hollowstar if inside outer radius.
        2. Wall avoidance: Repel from arena boundaries.
        3. Dogfighting: Intercept target, aim blasters, match velocity.
        """
        state = InputState()

        # Desired movement force vector (Fx, Fy)
        desired_fx = 0.0
        desired_fy = 0.0

        # --- 1. Hollowstar Repulsion ---
        if hollowstar:
            dx_hs = bot.center_x - hollowstar.center_x
            dy_hs = bot.center_y - hollowstar.center_y
            dist_hs = math.hypot(dx_hs, dy_hs)

            if dist_hs < tuning.GRAVITY_OUTER_RADIUS:
                # Strong repulsion away from black hole
                weight = ((tuning.GRAVITY_OUTER_RADIUS - dist_hs) / tuning.GRAVITY_OUTER_RADIUS) ** 2
                desired_fx += (dx_hs / max(dist_hs, 1)) * weight * 3.0
                desired_fy += (dy_hs / max(dist_hs, 1)) * weight * 3.0

        # --- 2. Wall Avoidance ---
        wall_margin = 120.0
        if bot.center_x < ARENA_LEFT + wall_margin:
            desired_fx += 1.5
        elif bot.center_x > ARENA_RIGHT - wall_margin:
            desired_fx -= 1.5

        if bot.center_y < ARENA_BOTTOM + wall_margin:
            desired_fy += 1.5
        elif bot.center_y > ARENA_TOP - wall_margin:
            desired_fy -= 1.5

        # --- 3. Target Dogfighting ---
        if target and target.alive:
            # Lead intercept calculation
            dx = target.center_x - bot.center_x
            dy = target.center_y - bot.center_y
            dist = math.hypot(dx, dy)

            # Ideal engagement distance is ~250-350 pixels
            ideal_dist = 280.0
            dist_error = dist - ideal_dist

            target_fx = (dx / max(dist, 1)) * (dist_error / 300.0)
            target_fy = (dy / max(dist, 1)) * (dist_error / 300.0)

            desired_fx += target_fx
            desired_fy += target_fy

            # Aim nose directly at target
            aim_angle = math.degrees(math.atan2(dx, dy))
            angle_diff = (aim_angle - bot.angle) % 360
            if angle_diff > 180:
                angle_diff -= 360

            # Steering
            if angle_diff > 4.0:
                state.rotation = 1.0
            elif angle_diff < -4.0:
                state.rotation = -1.0
            else:
                state.rotation = 0.0

            # Fire blaster if aimed well and in range
            rad = math.radians(bot.angle)
            alignment = (math.sin(rad) * (dx / max(dist, 1))) + (math.cos(rad) * (dy / max(dist, 1)))
            if dist < 650 and alignment > 0.94 and bot.fire_cooldown == 0:
                state.fire = True
        else:
            # Orbit or patrol arena
            aim_angle = math.degrees(math.atan2(desired_fx, desired_fy)) if (desired_fx or desired_fy) else 0
            angle_diff = (aim_angle - bot.angle) % 360
            if angle_diff > 180:
                angle_diff -= 360
            state.rotation = 1.0 if angle_diff > 5.0 else (-1.0 if angle_diff < -5.0 else 0.0)

        # --- 4. Thrust Control ---
        rad = math.radians(bot.angle)
        heading_x = math.sin(rad)
        heading_y = math.cos(rad)

        speed = math.hypot(bot.velocity_x, bot.velocity_y)
        thrust_alignment = (heading_x * desired_fx) + (heading_y * desired_fy)

        if thrust_alignment > 0.3 and speed < 6.0:
            state.thrust = 1.0
        else:
            state.thrust = 0.0

        return state
