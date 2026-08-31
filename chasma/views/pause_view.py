import arcade

from chasma.config.settings import *
from chasma.config.colors import ChasmaColors


class PauseView(arcade.View):
    """Pause overlay that freezes gameplay."""

    def __init__(self, game_view):
        super().__init__()
        self.game_view = game_view
        self.start_held = True  # Start was just pressed to get here

        self.paused_text = arcade.Text(
            "PAUSED",
            SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 20,
            arcade.color.WHITE, font_size=48,
            anchor_x="center", anchor_y="center",
        )
        self.prompt_text = arcade.Text(
            "ESC / START to resume  |  Q / BACK to quit",
            SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 40,
            arcade.color.GRAY, font_size=16,
            anchor_x="center", anchor_y="center",
        )

    def on_update(self, delta_time):
        # Check if all controllers have released Start
        if self.start_held:
            controllers = self.window.menu_controllers
            if controllers:
                if not any(c.start for c in controllers):
                    self.start_held = False
            else:
                self.start_held = False

    def on_draw(self):
        # Draw the frozen game underneath
        self.game_view.on_draw()

        # Dim overlay
        arcade.draw_lrbt_rectangle_filled(
            0, SCREEN_WIDTH, 0, SCREEN_HEIGHT,
            (0, 0, 0, 150),
        )

        self.paused_text.draw()
        self.prompt_text.draw()

    def _resume(self):
        self.game_view.pause_held = True  # Prevent immediate re-pause
        self.window.show_view(self.game_view)

    def _quit_to_title(self):
        from chasma.views.title_view import TitleView
        self.window.show_view(TitleView())

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            self._resume()
        elif key == arcade.key.Q:
            self._quit_to_title()

    def on_button_press(self, controller, button):
        if self.start_held:
            return  # Ignore until Start is released first
        if button == "start":
            self._resume()
        elif button == "back":
            self._quit_to_title()
