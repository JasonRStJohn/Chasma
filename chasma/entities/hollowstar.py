import arcade
import math
import random

from chasma.config.settings import *
from chasma.config.colors import ChasmaColors
from chasma.entities.base_entity import BaseEntity


class Hollowstar(BaseEntity):
    """
    The Hollowstar — a black hole that wanders the arena.
    Emits a gravity field that pulls ships toward it.
    Ships that cross GRAVITY_INNER_RADIUS enter a spiral death sequence.
    """

    def __init__(self, center_x, center_y):
        super().__init__(center_x, center_y)
        self.spin_angle = 0.0
        self.wander_angle = random.uniform(0, 2 * math.pi)
        self.velocity_x = math.cos(self.wander_angle) * HOLLOWSTAR_SPEED
        self.velocity_y = math.sin(self.wander_angle) * HOLLOWSTAR_SPEED

    def update(self):
        """Wander the arena with gentle random direction changes and center pull."""
        self.spin_angle += HOLLOWSTAR_SPIN_SPEED

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

    def draw(self):
        """Draw the black hole: accretion disc, event horizon, glow ring, singularity."""
        angle_rad = math.radians(self.spin_angle)

        # 1. Accretion disc — warm amber ellipse, rotated and slightly squashed
        disc_a = HOLLOWSTAR_DISC_OUTER
        disc_b = int(HOLLOWSTAR_DISC_OUTER * 0.55)

        # Draw filled outer disc (amber)
        arcade.draw_ellipse_filled(
            self.center_x, self.center_y,
            disc_a * 2, disc_b * 2,
            ChasmaColors.HOLLOWSTAR_DISC,
            tilt_angle=self.spin_angle,
        )

        # 2. Event horizon — black circle punches out the center
        arcade.draw_circle_filled(
            self.center_x, self.center_y,
            HOLLOWSTAR_DISC_INNER,
            arcade.color.BLACK,
        )

        # 3. Glow ring — thin cold blue-white outline
        arcade.draw_circle_outline(
            self.center_x, self.center_y,
            HOLLOWSTAR_GLOW_RADIUS,
            ChasmaColors.HOLLOWSTAR_GLOW,
            border_width=2,
        )

        # 4. Singularity — pure black center dot
        arcade.draw_circle_filled(
            self.center_x, self.center_y,
            HOLLOWSTAR_SINGULARITY,
            arcade.color.BLACK,
        )
