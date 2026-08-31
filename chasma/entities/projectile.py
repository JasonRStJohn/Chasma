import arcade
import math

from chasma.config.settings import *
from chasma.entities.base_entity import BaseEntity


class Projectile(BaseEntity):
    """
    A blaster shot — a colored dash that flies forward and knocks
    opponents back on impact.
    """

    def __init__(self, owner, color, x, y, angle):
        super().__init__(x, y)
        self.owner = owner
        self.color = color
        self.angle = angle
        self.lifetime = BLASTER_LIFETIME
        self.alive = True

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

    def draw(self):
        """Draw the dash as a short thick line in the owner's color."""
        if not self.alive:
            return

        angle_rad = math.radians(self.angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

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

    def on_bounce_x(self):
        """Update angle after bouncing off a vertical wall."""
        self.angle = math.degrees(math.atan2(self.velocity_x, self.velocity_y))

    def on_bounce_y(self):
        """Update angle after bouncing off a horizontal wall."""
        self.angle = math.degrees(math.atan2(self.velocity_x, self.velocity_y))

    def check_hit(self, player):
        """Check if this projectile hit a player (not its owner)."""
        if player is self.owner or not player.alive or not self.alive:
            return False
        dx = self.center_x - player.center_x
        dy = self.center_y - player.center_y
        return math.hypot(dx, dy) < BLASTER_HIT_RADIUS

    def kill(self):
        """Remove this projectile."""
        self.alive = False
