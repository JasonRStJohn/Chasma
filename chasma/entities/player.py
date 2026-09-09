import arcade
import math
from arcade.shape_list import ShapeElementList, create_polygon

from chasma.config.settings import *
from chasma.config import tuning
from chasma.config.colors import ChasmaColors
from chasma.entities.base_entity import BaseEntity


class Player(BaseEntity):
    """
    The player ship class. Uses manual physics and a ShapeElementList
    for custom drawing.
    """
    def __init__(self, player_color, center_x, center_y):
        super().__init__(center_x, center_y)

        self.player_color = player_color
        self._current_scale = getattr(tuning, "SHIP_SCALE", 2.0)
        self._build_shapes(self._current_scale)

        # --- Player-specific attributes ---
        self.thrust = 0
        self.lives = PLAYER_LIVES
        self.alive = True
        self.fire_cooldown = 0
        self.wants_to_fire = False
        self._fire_held = False
        self.spiraling = False
        self.spiral_timer = 0
        self.respawn_timer = -1   # -1 = not pending; >=0 = countdown to respawn

    def _build_shapes(self, scale):
        """Construct the polygon meshes at the current scale."""
        self.shape_list = ShapeElementList()
        s = float(scale)
        ship_points = ((-10 * s, -10 * s), (10 * s, -10 * s), (0, 20 * s))
        main_shape = create_polygon(ship_points, ChasmaColors.SHIP_GRAY)
        self.shape_list.append(main_shape)

        color_points = ((-10 * s, -10 * s), (10 * s, -10 * s), (0, -3 * s))
        color_shape = create_polygon(color_points, self.player_color)
        self.shape_list.append(color_shape)
        self._current_scale = s

    @property
    def collision_radius(self):
        return 14.0 * getattr(tuning, "SHIP_SCALE", 2.0)

    def apply_input(self, input_state):
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
            # Visual spin — actual velocity pull is applied from game_view
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

    def try_fire(self):
        """Attempt to fire. Returns a Projectile if successful, None otherwise.
        Only fires on the rising edge (press, not hold)."""
        if not self.alive or self.fire_cooldown > 0:
            return None
        if not self.wants_to_fire:
            self._fire_held = False
            return None
        if self._fire_held:
            return None
        self._fire_held = True

        from chasma.entities.projectile import Projectile

        self.fire_cooldown = BLASTER_COOLDOWN

        # Spawn projectile at the nose of the ship
        scale = getattr(tuning, "SHIP_SCALE", 2.0)
        nose_dist = 22 * scale  # just past the ship's tip
        spawn_x = self.center_x + math.sin(math.radians(self.angle)) * nose_dist
        spawn_y = self.center_y + math.cos(math.radians(self.angle)) * nose_dist

        return Projectile(
            owner=self,
            color=self.player_color,
            x=spawn_x,
            y=spawn_y,
            angle=self.angle,
        )

    def draw(self):
        """Draw the ship and thrust flame."""
        if not self.alive:
            return

        # Rebuild polygon meshes if SHIP_SCALE was tuned live
        current_scale = getattr(tuning, "SHIP_SCALE", 2.0)
        if self._current_scale != current_scale:
            self._build_shapes(current_scale)

        super().draw()

        # --- Thrust Flame ---
        if self.thrust > 0:
            scale = self._current_scale
            thrust_ratio = self.thrust / THRUST_FORCE
            flame_length = (FLAME_MIN_LENGTH + thrust_ratio * (FLAME_MAX_LENGTH - FLAME_MIN_LENGTH)) * (scale / 2.0)
            flame_half_w = (FLAME_WIDTH / 2.0) * (0.5 + 0.5 * thrust_ratio) * (scale / 2.0)

            # Flame points in local space (behind the ship)
            angle_rad = math.radians(self.angle)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)

            # Ship back center is at (0, -10 * scale) in local space
            back_y = -10.0 * scale
            # Rotate and translate each flame vertex
            def to_world(lx, ly):
                return (
                    self.center_x + lx * cos_a + ly * sin_a,
                    self.center_y - lx * sin_a + ly * cos_a,
                )

            p1 = to_world(-flame_half_w, back_y)
            p2 = to_world(flame_half_w, back_y)
            p3 = to_world(0, back_y - flame_length)

            arcade.draw_triangle_filled(
                p1[0], p1[1], p2[0], p2[1], p3[0], p3[1],
                arcade.color.RED,
            )

    def begin_spiral(self):
        """Enter the point-of-no-return spiral death sequence."""
        self.spiraling = True
        self.spiral_timer = tuning.SPIRAL_DURATION
        self.velocity_x = 0
        self.velocity_y = 0

    def respawn(self, x, y):
        """Reset player to a position after a death."""
        self.center_x = x
        self.center_y = y
        self.velocity_x = 0
        self.velocity_y = 0
        self.angle = 0
        self.thrust = 0
        self.spiraling = False
        self.spiral_timer = 0
        self.respawn_timer = -1

    def die(self):
        """Lose a life. Returns True if eliminated."""
        self.lives -= 1
        if self.lives <= 0:
            self.alive = False
            return True
        return False
