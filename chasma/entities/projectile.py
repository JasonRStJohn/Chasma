import arcade
import math

from chasma.config.settings import *
from chasma.core.simulation import ProjectileState


class Projectile(ProjectileState):
    """
    A blaster shot — a colored dash that flies forward and knocks
    opponents back on impact.
    Inherits movement, lifetime, and hit detection from ProjectileState.
    """

    def __init__(self, owner, color, x, y, angle):
        super().__init__(owner, color, x, y, angle)

    def draw(self):
        """Draw the dash as a short thick line in the owner's color."""
        if not self.alive:
            return

        angle_rad = math.radians(self.angle)

        # Dash extends from center backward/forward along the angle
        half_len = BLASTER_LENGTH / 2
        # "Forward" in this coordinate system
        dx = math.sin(angle_rad) * half_len
        dy = math.cos(angle_rad) * half_len

        x1 = self.center_x - dx
        y1 = self.center_y - dy
        x2 = self.center_x + dx
        y2 = self.center_y + dy

        arcade.draw_line(x1, y1, x2, y2, self.color, BLASTER_WIDTH)
