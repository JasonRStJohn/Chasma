import arcade
import math
from arcade.shape_list import ShapeElementList, create_polygon

from chasma.config.settings import *
from chasma.config import tuning
from chasma.config.colors import ChasmaColors
from chasma.core.simulation import ShipState
from chasma.entities.projectile import Projectile


class Player(ShipState):
    """
    The player ship class. Inherits physics and combat state from ShipState,
    and uses an Arcade ShapeElementList for custom desktop drawing.
    """
    def __init__(self, player_color, center_x, center_y, slot=0):
        super().__init__(player_color=player_color, center_x=center_x, center_y=center_y, slot=slot)
        self.shape_list = ShapeElementList()
        self._current_scale = getattr(tuning, "SHIP_SCALE", 2.0)
        self._build_shapes(self._current_scale)

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

    def try_fire(self, projectile_cls=Projectile):
        """Attempt to fire, defaulting to the graphical Projectile class on desktop."""
        return super().try_fire(projectile_cls=projectile_cls)

    def draw(self):
        """Draw the ship and thrust flame."""
        if not self.alive:
            return

        # Rebuild polygon meshes if SHIP_SCALE was tuned live
        current_scale = getattr(tuning, "SHIP_SCALE", 2.0)
        if self._current_scale != current_scale:
            self._build_shapes(current_scale)

        self.shape_list.center_x = self.center_x
        self.shape_list.center_y = self.center_y
        self.shape_list.angle = self.angle
        self.shape_list.draw()

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
