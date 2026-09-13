import math
import random
import numpy as np
import gymnasium as gym
from gymnasium import spaces

from chasma.config.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    ARENA_LEFT,
    ARENA_RIGHT,
    ARENA_BOTTOM,
    ARENA_TOP,
    ROTATION_SPEED,
    THRUST_FORCE,
    DRAG_COEFFICIENT,
    BLASTER_SPEED,
    BLASTER_COOLDOWN,
    BLASTER_KNOCKBACK,
)
from chasma.config import tuning


class HeadlessShip:
    """Lightweight physics representation of a ship for fast headless simulation."""

    def __init__(self, x=0.0, y=0.0, angle=0.0):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.angle = float(angle)
        self.thrust = 0.0
        self.change_angle = 0.0
        self.fire_cooldown = 0
        self.alive = True
        self.spiraling = False

    def step(self):
        if not self.alive:
            return

        self.angle += self.change_angle

        if self.thrust > 0:
            rad = math.radians(self.angle)
            self.vx += math.sin(rad) * self.thrust
            self.vy += math.cos(rad) * self.thrust

        self.vx *= DRAG_COEFFICIENT
        self.vy *= DRAG_COEFFICIENT

        # Speed clamp to keep flight stable
        speed = math.hypot(self.vx, self.vy)
        if speed > 8.0:
            scale = 8.0 / speed
            self.vx *= scale
            self.vy *= scale

        self.x += self.vx
        self.y += self.vy

        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        # Bounce off arena walls
        if self.x < ARENA_LEFT:
            self.x = ARENA_LEFT
            self.vx *= -0.5
        elif self.x > ARENA_RIGHT:
            self.x = ARENA_RIGHT
            self.vx *= -0.5

        if self.y < ARENA_BOTTOM:
            self.y = ARENA_BOTTOM
            self.vy *= -0.5
        elif self.y > ARENA_TOP:
            self.y = ARENA_TOP
            self.vy *= -0.5


class ChasmaArenaEnv(gym.Env):
    """
    Headless Gymnasium training environment for Chasma.
    Simulates the arena walls, Hollowstar gravity dynamics, and dogfighting against a sparring opponent.
    """

    metadata = {"render_modes": []}

    def __init__(self):
        super().__init__()

        self.max_speed = 10.0
        self.screen_diag = math.hypot(SCREEN_WIDTH, SCREEN_HEIGHT)

        # Actions: [Steering (0: none, 1: left, 2: right), Thrust (0: off, 1: on), Fire (0: off, 1: on)]
        self.action_space = spaces.MultiDiscrete([3, 2, 2])

        # 14 normalized observation floats matching AIController._build_observation
        self.observation_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(14,),
            dtype=np.float32,
        )

        self.agent = HeadlessShip()
        self.opponent = HeadlessShip()
        self.hs_x = SCREEN_WIDTH / 2.0
        self.hs_y = SCREEN_HEIGHT / 2.0
        self.hs_vx = 0.5
        self.hs_vy = 0.3

        self.agent_projectiles = []  # list of [x, y, vx, vy, lifetime]
        self.prev_dist = 0.0
        self.ticks = 0
        self.max_ticks = 600

    def _get_obs(self) -> np.ndarray:
        rad = math.radians(self.agent.angle)
        heading_x = math.sin(rad)
        heading_y = math.cos(rad)

        norm_vx = float(np.clip(self.agent.vx / self.max_speed, -1.0, 1.0))
        norm_vy = float(np.clip(self.agent.vy / self.max_speed, -1.0, 1.0))

        # Opponent relative vector
        dx_t = self.opponent.x - self.agent.x
        dy_t = self.opponent.y - self.agent.y
        dist_t = math.hypot(dx_t, dy_t)
        norm_dx_t = float(np.clip(dx_t / SCREEN_WIDTH, -1.0, 1.0))
        norm_dy_t = float(np.clip(dy_t / SCREEN_HEIGHT, -1.0, 1.0))
        norm_dist_t = float(np.clip(dist_t / self.screen_diag, 0.0, 1.0))

        rel_vx = float(np.clip((self.opponent.vx - self.agent.vx) / self.max_speed, -1.0, 1.0))
        rel_vy = float(np.clip((self.opponent.vy - self.agent.vy) / self.max_speed, -1.0, 1.0))
        alignment = (heading_x * (dx_t / max(dist_t, 1))) + (heading_y * (dy_t / max(dist_t, 1)))

        # Hollowstar relative vector
        dx_hs = self.hs_x - self.agent.x
        dy_hs = self.hs_y - self.agent.y
        dist_hs = math.hypot(dx_hs, dy_hs)
        norm_dx_hs = float(np.clip(dx_hs / SCREEN_WIDTH, -1.0, 1.0))
        norm_dy_hs = float(np.clip(dy_hs / SCREEN_HEIGHT, -1.0, 1.0))
        norm_dist_hs = float(np.clip(dist_hs / self.screen_diag, 0.0, 1.0))
        in_gravity = 1.0 if dist_hs < tuning.GRAVITY_OUTER_RADIUS else 0.0

        return np.array(
            [
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
            ],
            dtype=np.float32,
        )

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.ticks = 0
        self.agent_projectiles.clear()

        # Spawn agent in bottom-left zone
        self.agent.x = random.uniform(ARENA_LEFT + 100, ARENA_LEFT + 400)
        self.agent.y = random.uniform(ARENA_BOTTOM + 100, ARENA_BOTTOM + 400)
        self.agent.vx = 0.0
        self.agent.vy = 0.0
        self.agent.angle = random.uniform(0, 360)
        self.agent.alive = True

        # Spawn opponent in top-right zone
        self.opponent.x = random.uniform(ARENA_RIGHT - 400, ARENA_RIGHT - 100)
        self.opponent.y = random.uniform(ARENA_TOP - 400, ARENA_TOP - 100)
        self.opponent.vx = random.uniform(-1.0, 1.0)
        self.opponent.vy = random.uniform(-1.0, 1.0)
        self.opponent.angle = random.uniform(0, 360)
        self.opponent.alive = True

        # Center Hollowstar
        self.hs_x = SCREEN_WIDTH / 2.0
        self.hs_y = SCREEN_HEIGHT / 2.0

        self.prev_dist = math.hypot(self.opponent.x - self.agent.x, self.opponent.y - self.agent.y)
        return self._get_obs(), {}

    def step(self, action):
        self.ticks += 1
        steering, thrust, fire = action

        # 1. Apply Agent controls
        if steering == 1:
            self.agent.change_angle = -ROTATION_SPEED
        elif steering == 2:
            self.agent.change_angle = ROTATION_SPEED
        else:
            self.agent.change_angle = 0.0

        self.agent.thrust = THRUST_FORCE if thrust == 1 else 0.0

        # Fire blaster
        if fire == 1 and self.agent.fire_cooldown == 0:
            self.agent.fire_cooldown = BLASTER_COOLDOWN
            rad = math.radians(self.agent.angle)
            proj_vx = math.sin(rad) * BLASTER_SPEED + self.agent.vx * 0.5
            proj_vy = math.cos(rad) * BLASTER_SPEED + self.agent.vy * 0.5
            self.agent_projectiles.append([self.agent.x, self.agent.y, proj_vx, proj_vy, 60])

        # 2. Opponent heuristic sparring movement (Dynamic combat flybys)
        opp_dx = self.agent.x - self.opponent.x
        opp_dy = self.agent.y - self.opponent.y
        opp_dist = math.hypot(opp_dx, opp_dy)
        direct_angle = math.degrees(math.atan2(opp_dx, opp_dy))

        # Circle-strafe offset when in mid range: aim slightly off-axis to fly orbital arcs
        if 140.0 <= opp_dist <= 350.0:
            target_heading = (direct_angle + 55.0) % 360  # Flanking orbital path
        elif opp_dist < 140.0:
            target_heading = (direct_angle + 120.0) % 360  # Jousting breakaway
        else:
            target_heading = direct_angle  # Direct pursuit when far away

        diff = (target_heading - self.opponent.angle) % 360
        if diff > 180:
            diff -= 360
        self.opponent.change_angle = ROTATION_SPEED if diff > 6.0 else (-ROTATION_SPEED if diff < -6.0 else 0)

        # Keep opponent moving dynamically so it never stalls into a stationary target
        opp_speed = math.hypot(self.opponent.vx, self.opponent.vy)
        if opp_dist > 350.0:
            self.opponent.thrust = THRUST_FORCE if abs(diff) < 45.0 else 0.0
        elif 140.0 <= opp_dist <= 350.0:
            self.opponent.thrust = THRUST_FORCE if (opp_speed < 4.5 and abs(diff) < 60.0) else 0.0
        else:
            self.opponent.thrust = THRUST_FORCE if opp_speed < 5.0 else 0.0

        # 3. Apply Hollowstar gravity
        for ship in (self.agent, self.opponent):
            dx_hs = self.hs_x - ship.x
            dy_hs = self.hs_y - ship.y
            dist_hs = math.hypot(dx_hs, dy_hs)
            if dist_hs < tuning.GRAVITY_OUTER_RADIUS:
                force = tuning.GRAVITY_STRENGTH / max(dist_hs, tuning.GRAVITY_MIN_DIST) ** 2
                ship.vx += (dx_hs / max(dist_hs, 1)) * force
                ship.vy += (dy_hs / max(dist_hs, 1)) * force

        # 4. Advance physics
        self.agent.step()
        self.opponent.step()

        # Hollowstar slight wander
        self.hs_x += self.hs_vx
        self.hs_y += self.hs_vy
        if self.hs_x < ARENA_LEFT + 200 or self.hs_x > ARENA_RIGHT - 200:
            self.hs_vx *= -1
        if self.hs_y < ARENA_BOTTOM + 200 or self.hs_y > ARENA_TOP - 200:
            self.hs_vy *= -1

        # 5. Update Projectiles & check hits
        hit_opponent = False
        remaining_projectiles = []
        for p in self.agent_projectiles:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 1
            # Check hit on opponent (radius synchronized with 2x scale)
            hit_dist = math.hypot(p[0] - self.opponent.x, p[1] - self.opponent.y)
            if hit_dist < 28.0:
                hit_opponent = True
                self.opponent.vx += (p[2] / BLASTER_SPEED) * BLASTER_KNOCKBACK
                self.opponent.vy += (p[3] / BLASTER_SPEED) * BLASTER_KNOCKBACK
                continue
            if p[4] > 0 and ARENA_LEFT <= p[0] <= ARENA_RIGHT and ARENA_BOTTOM <= p[1] <= ARENA_TOP:
                remaining_projectiles.append(p)
        self.agent_projectiles = remaining_projectiles

        # 6. Evaluate distances & rewards
        dx = self.opponent.x - self.agent.x
        dy = self.opponent.y - self.agent.y
        current_dist = math.hypot(dx, dy)

        rad = math.radians(self.agent.angle)
        alignment = (math.sin(rad) * (dx / max(current_dist, 1))) + (math.cos(rad) * (dy / max(current_dist, 1)))

        hs_dist = math.hypot(self.hs_x - self.agent.x, self.hs_y - self.agent.y)
        speed = math.hypot(self.agent.vx, self.agent.vy)

        reward = 0.0
        terminated = False

        # --- A. Hollowstar Danger ---
        if hs_dist < tuning.GRAVITY_INNER_RADIUS:
            # Fatal death in singularity
            reward -= 15.0
            terminated = True
        elif hs_dist < tuning.GRAVITY_OUTER_RADIUS:
            # Penalty for lingering in gravitational vortex
            reward -= 0.02 * ((tuning.GRAVITY_OUTER_RADIUS - hs_dist) / tuning.GRAVITY_OUTER_RADIUS)

        # --- B. Blaster Hits & Kinetic Aiming ---
        if hit_opponent:
            reward += 10.0

        # Only reward good aim if actively flying; camping stationary turrets get 0 aim points!
        if speed >= 1.2:
            reward += max(0.0, alignment) * 0.04

        # --- C. Kinetic Movement vs Stagnation (Anti-Camping) ---
        if speed < 1.2:
            # Stagnation penalty (sitting still is penalized)
            reward -= 0.03 * (1.2 - speed)
        elif 1.8 <= speed <= 5.2:
            # Cruising reward: encourages healthy dogfighting momentum
            reward += 0.02

        # --- D. Dogfight Engagement Distance & Interception ---
        closing_vel = (self.agent.vx * dx + self.agent.vy * dy) / max(current_dist, 1)

        if current_dist > 350.0:
            # Far range: reward closing in, penalize fleeing or stalling
            if closing_vel > 0.6:
                reward += 0.03 * min(closing_vel / 4.0, 1.0)
            elif closing_vel < -0.6:
                reward -= 0.015
        elif current_dist < 100.0:
            # Ramming avoidance: penalize collision
            reward -= 0.03
        else:
            # Sweet spot (100 - 350 px): optimal dogfight engagement range
            reward += 0.025

        # --- E. Throttle Discipline ---
        if thrust == 1:
            if speed > 6.0:
                reward -= 0.02  # Prevent out-of-control missile overspeeding
            if alignment < -0.3:
                reward -= 0.02  # Discourage burning thrust straight away from target

        self.prev_dist = current_dist
        truncated = self.ticks >= self.max_ticks

        return self._get_obs(), reward, terminated, truncated, {}
