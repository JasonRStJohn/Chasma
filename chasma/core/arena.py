import arcade

from chasma.config.settings import *
from chasma.config.colors import ChasmaColors
from chasma.core.simulation import ArenaBounds


class Arena(ArenaBounds):
    """
    Owns the arena geometry — grid, walls, and boundary collision.
    Inherits boundary collision and warp math from ArenaBounds.
    """

    def __init__(self):
        super().__init__()

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
