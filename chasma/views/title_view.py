import arcade

from chasma.config.settings import *
from chasma.config.colors import ChasmaColors
from chasma.core.arena import Arena


class TitleView(arcade.View):
    """Title screen shown on startup."""

    def __init__(self):
        super().__init__()
        self.arena = Arena()

        self.title_text = arcade.Text(
            "CHASMA",
            SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 60,
            arcade.color.WHITE, font_size=64,
            anchor_x="center", anchor_y="center",
            font_name="Kenney Future",
        )
        self.subtitle_text = arcade.Text(
            "Survive the Hollowstar",
            SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 10,
            ChasmaColors.GRID_BLUE, font_size=18,
            anchor_x="center", anchor_y="center",
        )
        self.prompt_text = arcade.Text(
            "Press ENTER or START",
            SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 80,
            arcade.color.GRAY, font_size=16,
            anchor_x="center", anchor_y="center",
        )

    def on_show_view(self):
        arcade.set_background_color(arcade.color.BLACK)

    def on_draw(self):
        self.clear()
        self.arena.draw()
        self.title_text.draw()
        self.subtitle_text.draw()
        self.prompt_text.draw()

    def _start_game(self):
        self.window.sound.play("menu_select")
        from chasma.views.game_view import GameView
        game_view = GameView()
        game_view.setup()
        self.window.show_view(game_view)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.RETURN:
            self._start_game()
        elif key == arcade.key.ESCAPE:
            arcade.close_window()

    def on_button_press(self, controller, button):
        if button == "start" or button == "a":
            self._start_game()
