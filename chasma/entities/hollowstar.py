import arcade
import math

from chasma.config.settings import *
from chasma.config.colors import ChasmaColors
from chasma.core.simulation import HollowstarState


class Hollowstar(HollowstarState):
    """
    The Hollowstar — a black hole that wanders the arena.
    Emits a gravity field that pulls ships toward it.
    Ships that cross GRAVITY_INNER_RADIUS enter a spiral death sequence.
    Inherits physics and wander logic from HollowstarState.
    """

    def __init__(self, center_x, center_y):
        super().__init__(center_x, center_y)

    def draw(self):
        """Draw the black hole: accretion disc, event horizon, glow ring, singularity."""
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
