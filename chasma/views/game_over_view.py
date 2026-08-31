import arcade

from chasma.config.settings import *
from chasma.config.colors import ChasmaColors


class GameOverView(arcade.View):
    """Game over screen shown when the game ends."""

    def __init__(self, winner=None):
        super().__init__()
        self.winner = winner

        if winner:
            title = "WINNER!"
            title_color = winner.player_color
        else:
            title = "GAME OVER"
            title_color = arcade.color.RED

        self.title_text = arcade.Text(
            title,
            SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 20,
            title_color, font_size=54,
            anchor_x="center", anchor_y="center",
        )
        self.prompt_text = arcade.Text(
            "ENTER / START to play again  |  ESC / BACK for title",
            SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 40,
            arcade.color.GRAY, font_size=16,
            anchor_x="center", anchor_y="center",
        )

    def on_show_view(self):
        arcade.set_background_color(arcade.color.BLACK)

    def on_draw(self):
        self.clear()
        self.title_text.draw()
        self.prompt_text.draw()

    def _play_again(self):
        self.window.sound.play("menu_select")
        from chasma.views.game_view import GameView
        game_view = GameView()
        game_view.setup()
        self.window.show_view(game_view)

    def _quit_to_title(self):
        from chasma.views.title_view import TitleView
        self.window.show_view(TitleView())

    def on_key_press(self, key, modifiers):
        if key == arcade.key.RETURN:
            self._play_again()
        elif key == arcade.key.ESCAPE:
            self._quit_to_title()

    def on_button_press(self, controller, button):
        if button == "start" or button == "a":
            self._play_again()
        elif button == "back":
            self._quit_to_title()
