import math
from arcade.shape_list import ShapeElementList


class BaseEntity:
    """
    Base class for all game entities. Provides position, velocity,
    angle, and ShapeElementList-based drawing.
    """

    def __init__(self, center_x=0, center_y=0):
        self.center_x = center_x
        self.center_y = center_y
        self.velocity_x = 0
        self.velocity_y = 0
        self.angle = 0
        self.change_angle = 0
        self.shape_list = ShapeElementList()

    def update_physics(self):
        """Apply velocity to position."""
        self.center_x += self.velocity_x
        self.center_y += self.velocity_y

    def draw(self):
        """Sync shape_list transform and draw."""
        self.shape_list.center_x = self.center_x
        self.shape_list.center_y = self.center_y
        self.shape_list.angle = self.angle
        self.shape_list.draw()
