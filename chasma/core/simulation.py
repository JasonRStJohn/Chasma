"""
Pure Python headless physics and match simulation kernel for Chasma.

This module has ZERO dependencies on `arcade` or OpenGL.
It serves as the single authoritative source of truth for:
1. The Desktop Arcade game (`GameView` in `chasma/views/game_view.py`)
2. The Online Authoritative Multiplayer Server (`online/server/`)
3. Headless testing and AI evaluation
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Type, Union

from chasma.config.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    ARENA_LEFT,
    ARENA_RIGHT,
    ARENA_BOTTOM,
    ARENA_TOP,
    GRID_SPACING,
    WALL_THICKNESS,
    ROTATION_SPEED,
    THRUST_FORCE,
    DRAG_COEFFICIENT,
    HOLLOWSTAR_SPEED,
    HOLLOWSTAR_WANDER_STRENGTH,
    HOLLOWSTAR_SPIN_SPEED,
    HOLLOWSTAR_CENTER_PULL,
    RESPAWN_DELAY,
    PLAYER_LIVES,
    PLAYER_COLORS,
    PLAYER_SPAWNS,
    BLASTER_SPEED,
    BLASTER_LIFETIME,
    BLASTER_KNOCKBACK,
    BLASTER_COOLDOWN,
    BLASTER_HIT_RADIUS,
)
from chasma.config import tuning
from chasma.config.colors import ChasmaColors


@dataclass
class InputState:
    """Unified input state for one player, per frame."""
    rotation: float = 0.0   # -1.0 (left) to 1.0 (right)
    thrust: float = 0.0     # 0.0 to 1.0
    fire: bool = False
    pause: bool = False


COLOR_MAP = {
    "PLAYER1_YELLOW": ChasmaColors.PLAYER1_YELLOW,
    "PLAYER2_RED": ChasmaColors.PLAYER2_RED,
    "PLAYER3_BLUE": ChasmaColors.PLAYER3_BLUE,
    "PLAYER4_GREEN": ChasmaColors.PLAYER4_GREEN,
}


class PhysicsEntity:
    """Pure Python base entity with position, velocity, and angle."""

    def __init__(self, center_x: float = 0.0, center_y: float = 0.0):
        self.center_x: float = float(center_x)
        self.center_y: float = float(center_y)
        self.velocity_x: float = 0.0
        self.velocity_y: float = 0.0
        self.angle: float = 0.0
        self.change_angle: float = 0.0

    def update_physics(self):
        """Apply velocity to position."""
        self.center_x += self.velocity_x
        self.center_y += self.velocity_y


class ArenaBounds:
    """
    Pure Python arena geometry — grid warp math, walls, and boundary collision.
    """

    def __init__(self):
        self.left = ARENA_LEFT
        self.right = ARENA_RIGHT
        self.top = ARENA_TOP
        self.bottom = ARENA_BOTTOM
        self.grid_spacing = GRID_SPACING
        self.wall_thickness = WALL_THICKNESS

    def _warp_point(self, px: float, py: float, hx: float, hy: float):
        """Displace a grid vertex toward the Hollowstar."""
        dx = px - hx
        dy = py - hy
        dist = max(math.hypot(dx, dy), 1)
        warp = tuning.GRID_WARP_STRENGTH / (dist + tuning.GRID_WARP_FALLOFF)
        return px - dx / dist * warp, py - dy / dist * warp

    def bounce(self, entity: PhysicsEntity, dampening: float = 1.0) -> bool:
        """
        Bounce an entity off the arena walls.
        dampening=1.0 is a perfect bounce, 0.5 loses half velocity, etc.
        Calls entity.on_bounce_x/on_bounce_y if they exist.
        Returns True if the entity bounced off any wall.
        """
        bounced_x = False
        bounced_y = False

        if entity.center_x < self.left:
            entity.center_x = self.left
            entity.velocity_x *= -dampening
            bounced_x = True
        elif entity.center_x > self.right:
            entity.center_x = self.right
            entity.velocity_x *= -dampening
            bounced_x = True
        if entity.center_y < self.bottom:
            entity.center_y = self.bottom
            entity.velocity_y *= -dampening
            bounced_y = True
        elif entity.center_y > self.top:
            entity.center_y = self.top
            entity.velocity_y *= -dampening
            bounced_y = True

        if bounced_x and hasattr(entity, "on_bounce_x"):
            entity.on_bounce_x()
        if bounced_y and hasattr(entity, "on_bounce_y"):
            entity.on_bounce_y()

        return bounced_x or bounced_y


class HollowstarState(PhysicsEntity):
    """
    Pure Python Hollowstar state and wander physics.
    """

    def __init__(self, center_x: float, center_y: float):
        super().__init__(center_x, center_y)
        self.spin_angle: float = 0.0
        self.wander_angle: float = random.uniform(0, 2 * math.pi)
        self.velocity_x = math.cos(self.wander_angle) * HOLLOWSTAR_SPEED
        self.velocity_y = math.sin(self.wander_angle) * HOLLOWSTAR_SPEED

    def update(self):
        """Wander the arena with gentle random direction changes and center pull."""
        self.spin_angle = (self.spin_angle + HOLLOWSTAR_SPIN_SPEED) % 360.0

        self.wander_angle += random.uniform(
            -HOLLOWSTAR_WANDER_STRENGTH, HOLLOWSTAR_WANDER_STRENGTH
        )

        self.velocity_x = math.cos(self.wander_angle) * HOLLOWSTAR_SPEED
        self.velocity_y = math.sin(self.wander_angle) * HOLLOWSTAR_SPEED

        # Soft pull toward arena center so it doesn't hug walls
        cx = (ARENA_LEFT + ARENA_RIGHT) / 2
        cy = (ARENA_BOTTOM + ARENA_TOP) / 2
        self.velocity_x += (cx - self.center_x) * HOLLOWSTAR_CENTER_PULL
        self.velocity_y += (cy - self.center_y) * HOLLOWSTAR_CENTER_PULL

        self.update_physics()

    def on_bounce_x(self):
        self.wander_angle = math.atan2(self.velocity_y, self.velocity_x)

    def on_bounce_y(self):
        self.wander_angle = math.atan2(self.velocity_y, self.velocity_x)


class ProjectileState(PhysicsEntity):
    """
    Pure Python blaster projectile state and hit detection.
    """
    _next_id: int = 1

    def __init__(self, owner, color, x: float, y: float, angle: float):
        super().__init__(x, y)
        self.id: int = ProjectileState._next_id
        ProjectileState._next_id += 1
        self.owner = owner
        self.owner_slot: int = getattr(owner, "slot", 0)
        self.color = color
        self.angle: float = float(angle)
        self.lifetime: int = BLASTER_LIFETIME
        self.alive: bool = True

        # Fire in the direction the ship is facing
        self.velocity_x = math.sin(math.radians(angle)) * BLASTER_SPEED
        self.velocity_y = math.cos(math.radians(angle)) * BLASTER_SPEED

    def update(self):
        """Move forward and count down lifetime."""
        if not self.alive:
            return

        self.update_physics()
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False

    def on_bounce_x(self):
        """Update angle after bouncing off a vertical wall."""
        self.angle = math.degrees(math.atan2(self.velocity_x, self.velocity_y))

    def on_bounce_y(self):
        """Update angle after bouncing off a horizontal wall."""
        self.angle = math.degrees(math.atan2(self.velocity_x, self.velocity_y))

    def check_hit(self, player) -> bool:
        """Check if this projectile hit a player (not its owner)."""
        if player is self.owner or not player.alive or not self.alive:
            return False
        dx = self.center_x - player.center_x
        dy = self.center_y - player.center_y
        return math.hypot(dx, dy) < BLASTER_HIT_RADIUS

    def kill(self):
        """Remove this projectile."""
        self.alive = False


class ShipState(PhysicsEntity):
    """
    Pure Python player ship state and physics.
    """

    def __init__(self, player_color, center_x: float, center_y: float, slot: int = 0):
        super().__init__(center_x, center_y)
        self.slot: int = slot
        self.player_color = player_color
        self.name: str = f"P{slot + 1}"
        self.is_ai: bool = False

        # --- Player-specific attributes ---
        self.thrust: float = 0.0
        self.lives: int = PLAYER_LIVES
        self.alive: bool = True
        self.fire_cooldown: int = 0
        self.wants_to_fire: bool = False
        self._fire_held: bool = False
        self.spiraling: bool = False
        self.spiral_timer: int = 0
        self.respawn_timer: int = -1   # -1 = not pending; >=0 = countdown to respawn

    @property
    def collision_radius(self) -> float:
        return 14.0 * getattr(tuning, "SHIP_SCALE", 2.0)

    def apply_input(self, input_state: InputState):
        """Apply an InputState to set rotation and thrust."""
        if self.spiraling:
            return
        self.change_angle = input_state.rotation * ROTATION_SPEED
        self.thrust = input_state.thrust * THRUST_FORCE
        self.wants_to_fire = input_state.fire

    def update(self):
        """Update the ship's position and speed using manual physics."""
        if not self.alive:
            return

        if self.spiraling:
            # Visual spin — actual velocity pull is applied from simulation step
            self.angle += tuning.SPIRAL_SPIN_SPEED
            self.update_physics()
            return

        # Rotate the ship
        self.angle += self.change_angle

        # Apply thrust to calculate acceleration
        if self.thrust > 0:
            acceleration_x = math.sin(math.radians(self.angle)) * self.thrust
            acceleration_y = math.cos(math.radians(self.angle)) * self.thrust
            self.velocity_x += acceleration_x
            self.velocity_y += acceleration_y

        # Apply friction to the velocity
        self.velocity_x *= DRAG_COEFFICIENT
        self.velocity_y *= DRAG_COEFFICIENT

        # Tick cooldown
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        # Move
        self.update_physics()

    def try_fire(self, projectile_cls: Type[ProjectileState] = ProjectileState) -> Optional[ProjectileState]:
        """Attempt to fire. Returns a ProjectileState if successful, None otherwise.
        Only fires on the rising edge (press, not hold)."""
        if not self.alive or self.fire_cooldown > 0:
            return None
        if not self.wants_to_fire:
            self._fire_held = False
            return None
        if self._fire_held:
            return None
        self._fire_held = True

        self.fire_cooldown = BLASTER_COOLDOWN

        # Spawn projectile at the nose of the ship
        scale = getattr(tuning, "SHIP_SCALE", 2.0)
        nose_dist = 22 * scale  # just past the ship's tip
        spawn_x = self.center_x + math.sin(math.radians(self.angle)) * nose_dist
        spawn_y = self.center_y + math.cos(math.radians(self.angle)) * nose_dist

        return projectile_cls(
            owner=self,
            color=self.player_color,
            x=spawn_x,
            y=spawn_y,
            angle=self.angle,
        )

    def begin_spiral(self):
        """Enter the point-of-no-return spiral death sequence."""
        self.spiraling = True
        self.spiral_timer = tuning.SPIRAL_DURATION
        self.velocity_x = 0.0
        self.velocity_y = 0.0

    def respawn(self, x: float, y: float):
        """Reset player to a position after a death."""
        self.center_x = float(x)
        self.center_y = float(y)
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.angle = 0.0
        self.thrust = 0.0
        self.spiraling = False
        self.spiral_timer = 0
        self.respawn_timer = -1

    def die(self) -> bool:
        """Lose a life. Returns True if eliminated."""
        self.lives -= 1
        if self.lives <= 0:
            self.alive = False
            return True
        return False


@dataclass
class SimulationStepResult:
    """Outcome of a single 60Hz simulation step."""
    tick: int
    events: List[str] = field(default_factory=list)
    is_game_over: bool = False
    winner: Optional[ShipState] = None


class ChasmaSimulation:
    """
    Authoritative 4-player arena simulation.
    Used identically by both Desktop `GameView` and Online `GameRoom`.
    """

    TOTAL_PLAYERS = 4

    def __init__(
        self,
        num_human_players: int = 1,
        ship_cls: Type[ShipState] = ShipState,
        hollowstar_cls: Type[HollowstarState] = HollowstarState,
        projectile_cls: Type[ProjectileState] = ProjectileState,
        arena: Optional[ArenaBounds] = None,
        ai_controller=None,
    ):
        self.ship_cls = ship_cls
        self.hollowstar_cls = hollowstar_cls
        self.projectile_cls = projectile_cls
        self.arena = arena if arena is not None else ArenaBounds()

        if ai_controller is None:
            from chasma.ai.ai_controller import AIController
            self.ai_controller = AIController()
        else:
            self.ai_controller = ai_controller

        self.tick: int = 0
        self.players: List[ShipState] = []
        self.projectiles: List[ProjectileState] = []
        self.hollowstar: Optional[HollowstarState] = None
        self.is_game_over: bool = False
        self.winner: Optional[ShipState] = None

        self.reset(num_human_players=num_human_players)

    def reset(self, num_human_players: Optional[int] = None):
        """Reset the arena, ships, projectiles, and Hollowstar for a new match."""
        # Preserve current AI flags if num_human_players not explicitly passed
        prev_ai_flags = [p.is_ai for p in self.players] if self.players else None
        prev_names = [p.name for p in self.players] if self.players else None

        self.tick = 0
        self.projectiles = []
        self.is_game_over = False
        self.winner = None

        self.players = []
        for i in range(self.TOTAL_PLAYERS):
            color_name = PLAYER_COLORS[i]
            color = COLOR_MAP[color_name]
            spawn_x, spawn_y = PLAYER_SPAWNS[i]
            try:
                player = self.ship_cls(
                    player_color=color,
                    center_x=spawn_x,
                    center_y=spawn_y,
                    slot=i,
                )
            except TypeError:
                player = self.ship_cls(
                    player_color=color,
                    center_x=spawn_x,
                    center_y=spawn_y,
                )
                player.slot = i

            if num_human_players is not None:
                player.is_ai = i >= num_human_players
            elif prev_ai_flags is not None:
                player.is_ai = prev_ai_flags[i]
            else:
                player.is_ai = True

            if prev_names is not None:
                player.name = prev_names[i]
            else:
                player.name = f"P{i + 1} [AI]" if player.is_ai else f"P{i + 1}"

            self.players.append(player)

        self.hollowstar = self.hollowstar_cls(
            center_x=SCREEN_WIDTH / 2,
            center_y=SCREEN_HEIGHT / 2,
        )

    def step(
        self,
        input_states: Optional[Union[Sequence[InputState], Dict[int, InputState]]] = None,
    ) -> SimulationStepResult:
        """
        Advance the simulation by 1 tick (1/60th second).
        `input_states` can be a list of InputState (indexed by player slot) or a dict {slot: InputState}.
        """
        self.tick += 1
        events: List[str] = []

        if input_states is None:
            input_map: Dict[int, InputState] = {}
        elif isinstance(input_states, dict):
            input_map = input_states
        else:
            input_map = {i: state for i, state in enumerate(input_states)}

        # --- 1. Gravity field ---
        for player in self.players:
            if not player.alive or player.spiraling:
                continue
            dx = self.hollowstar.center_x - player.center_x
            dy = self.hollowstar.center_y - player.center_y
            distance = math.hypot(dx, dy)
            if distance < tuning.GRAVITY_OUTER_RADIUS and distance > 0:
                force = tuning.GRAVITY_STRENGTH / max(distance, tuning.GRAVITY_MIN_DIST) ** 2
                player.velocity_x += (dx / distance) * force
                player.velocity_y += (dy / distance) * force

        # --- 2. Apply input and update players ---
        for i, player in enumerate(self.players):
            # Respawn countdown — player is invisible until timer expires
            if not player.alive and player.respawn_timer >= 0:
                player.respawn_timer -= 1
                if player.respawn_timer < 0:
                    spawn_x, spawn_y = PLAYER_SPAWNS[i]
                    player.respawn(spawn_x, spawn_y)
                    player.alive = True

            if player.alive:
                if getattr(player, "is_ai", False):
                    ai_input = self.ai_controller.get_input_state(
                        player, self.players, self.hollowstar
                    )
                    player.apply_input(ai_input)
                elif i in input_map:
                    player.apply_input(input_map[i])
                else:
                    player.apply_input(InputState())

            player.update()
            if player.alive and not player.spiraling:
                self.arena.bounce(player, dampening=0.5)

            # --- Fire blasters ---
            proj = player.try_fire(projectile_cls=self.projectile_cls)
            if proj:
                self.projectiles.append(proj)
                events.append("fire")

        # --- 3. Ship-to-ship collisions ---
        for i in range(len(self.players)):
            p1 = self.players[i]
            if not p1.alive or p1.spiraling:
                continue
            for j in range(i + 1, len(self.players)):
                p2 = self.players[j]
                if not p2.alive or p2.spiraling:
                    continue

                dx = p2.center_x - p1.center_x
                dy = p2.center_y - p1.center_y
                dist = math.hypot(dx, dy)
                min_dist = p1.collision_radius + p2.collision_radius

                if dist < min_dist and dist > 0.0001:
                    # 1. Positional separation (prevent clipping)
                    overlap = min_dist - dist
                    nx = dx / dist
                    ny = dy / dist
                    p1.center_x -= nx * (overlap * 0.5)
                    p1.center_y -= ny * (overlap * 0.5)
                    p2.center_x += nx * (overlap * 0.5)
                    p2.center_y += ny * (overlap * 0.5)

                    # 2. Elastic bounce impulse with live-tunable strength
                    rvx = p2.velocity_x - p1.velocity_x
                    rvy = p2.velocity_y - p1.velocity_y
                    vel_along_normal = rvx * nx + rvy * ny

                    if vel_along_normal < 0:
                        restitution = 0.8
                        impulse_mag = -(1 + restitution) * vel_along_normal * 0.5
                        bump_boost = getattr(tuning, "SHIP_COLLISION_STRENGTH", 1.2)
                        total_impulse = (impulse_mag + 1.0) * bump_boost

                        p1.velocity_x -= nx * total_impulse
                        p1.velocity_y -= ny * total_impulse
                        p2.velocity_x += nx * total_impulse
                        p2.velocity_y += ny * total_impulse

                        events.append("hit")

        # --- 4. Spiral death sequence ---
        for player in self.players:
            if not player.alive:
                continue

            dx = self.hollowstar.center_x - player.center_x
            dy = self.hollowstar.center_y - player.center_y
            distance = math.hypot(dx, dy)

            if player.spiraling:
                # Pull hard toward center during spiral
                force = (
                    tuning.GRAVITY_STRENGTH
                    * tuning.SPIRAL_FORCE_MULTIPLIER
                    / max(distance, tuning.GRAVITY_MIN_DIST) ** 2
                )
                player.velocity_x += (dx / max(distance, 1)) * force
                player.velocity_y += (dy / max(distance, 1)) * force
                # Cap velocity so the ship doesn't overshoot the Hollowstar
                speed = math.hypot(player.velocity_x, player.velocity_y)
                if speed > tuning.MAX_SPIRAL_SPEED:
                    player.velocity_x = (player.velocity_x / speed) * tuning.MAX_SPIRAL_SPEED
                    player.velocity_y = (player.velocity_y / speed) * tuning.MAX_SPIRAL_SPEED
                player.spiral_timer -= 1
                if player.spiral_timer <= 0:
                    player.spiraling = False
                    player.velocity_x = 0.0
                    player.velocity_y = 0.0
                    player.alive = False   # ship disappears into the Hollowstar
                    eliminated = player.die()
                    events.append("death")
                    if not eliminated:
                        player.respawn_timer = RESPAWN_DELAY
            elif distance < tuning.GRAVITY_INNER_RADIUS:
                player.begin_spiral()
                events.append("suck")

        # --- 5. Update projectiles ---
        for proj in self.projectiles:
            proj.update()
            self.arena.bounce(proj, dampening=1.0)

        # Remove dead projectiles (timed out)
        self.projectiles = [p for p in self.projectiles if p.alive]

        # --- 6. Projectile-player collisions ---
        for proj in self.projectiles:
            for player in self.players:
                if proj.check_hit(player):
                    # Apply knockback in the direction the projectile is traveling
                    angle_rad = math.radians(proj.angle)
                    player.velocity_x += math.sin(angle_rad) * BLASTER_KNOCKBACK
                    player.velocity_y += math.cos(angle_rad) * BLASTER_KNOCKBACK
                    proj.kill()
                    events.append("hit")
                    break

        # Remove projectiles killed by player hits
        self.projectiles = [p for p in self.projectiles if p.alive]

        # --- 7. Update Hollowstar ---
        self.hollowstar.update()
        self.arena.bounce(self.hollowstar, dampening=1.0)

        # --- 8. Check for game over ---
        surviving = [p for p in self.players if p.lives > 0]
        if not self.is_game_over:
            if len(self.players) == 1 and len(surviving) == 0:
                self.is_game_over = True
                self.winner = None
                events.append("game_over")
            elif len(self.players) > 1 and len(surviving) <= 1:
                self.is_game_over = True
                self.winner = surviving[0] if surviving else None
                events.append("win" if self.winner else "game_over")

        return SimulationStepResult(
            tick=self.tick,
            events=events,
            is_game_over=self.is_game_over,
            winner=self.winner,
        )
