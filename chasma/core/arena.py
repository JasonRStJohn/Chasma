import arcade
import math

from chasma.config.settings import *
from chasma.config import tuning
from chasma.config.colors import ChasmaColors


class Arena:
    """
    Owns the arena geometry — grid, walls, and boundary collision.
    """

    def __init__(self):
        self.left = ARENA_LEFT
        self.right = ARENA_RIGHT
        self.top = ARENA_TOP
        self.bottom = ARENA_BOTTOM
        self.grid_spacing = GRID_SPACING
        self.wall_thickness = WALL_THICKNESS

    def _warp_point(self, px, py, hx, hy):
        """Displace a grid vertex toward the Hollowstar."""
        dx = px - hx
        dy = py - hy
        dist = max(math.hypot(dx, dy), 1)
        warp = tuning.GRID_WARP_STRENGTH / (dist + tuning.GRID_WARP_FALLOFF)
        return px - dx / dist * warp, py - dy / dist * warp

    def _draw_warped_line(self, x1, y1, x2, y2, hx, hy):
        """Draw a line as GRID_WARP_SEGMENTS warped segments."""
        n = GRID_WARP_SEGMENTS
        prev_x, prev_y = self._warp_point(x1, y1, hx, hy)
        for i in range(1, n + 1):
            t = i / n
            px = x1 + (x2 - x1) * t
            py = y1 + (y2 - y1) * t
            wx, wy = self._warp_point(px, py, hx, hy)
            arcade.draw_line(prev_x, prev_y, wx, wy, ChasmaColors.GRID_BLUE, 1)
            prev_x, prev_y = wx, wy

    def draw(self, hollowstar_x=None, hollowstar_y=None):
        """Draw the grid and arena walls."""
        warp = hollowstar_x is not None and hollowstar_y is not None

        # Vertical grid lines
        x = self.left
        while x <= self.right:
            if warp:
                self._draw_warped_line(x, self.bottom, x, self.top,
                                       hollowstar_x, hollowstar_y)
            else:
                arcade.draw_line(x, self.bottom, x, self.top,
                                 ChasmaColors.GRID_BLUE, 1)
            x += self.grid_spacing

        # Horizontal grid lines
        y = self.bottom
        while y <= self.top:
            if warp:
                self._draw_warped_line(self.left, y, self.right, y,
                                       hollowstar_x, hollowstar_y)
            else:
                arcade.draw_line(self.left, y, self.right, y,
                                 ChasmaColors.GRID_BLUE, 1)
            y += self.grid_spacing

        # Outer walls (never warped)
        arcade.draw_lrbt_rectangle_outline(
            self.left, self.right, self.bottom, self.top,
            ChasmaColors.GRID_BLUE, self.wall_thickness,
        )

    def bounce(self, entity, dampening=1.0):
        """
        Bounce an entity off the arena walls.
        dampening=1.0 is a perfect bounce, 0.5 loses half velocity, etc.
        Calls entity.on_bounce_x/on_bounce_y if they exist.
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

        if bounced_x and hasattr(entity, 'on_bounce_x'):
            entity.on_bounce_x()
        if bounced_y and hasattr(entity, 'on_bounce_y'):
            entity.on_bounce_y()
