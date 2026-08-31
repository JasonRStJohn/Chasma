import arcade

from chasma.config.settings import *
from chasma.systems.sound import SoundManager
from chasma.views.title_view import TitleView


class ChasmaGame(arcade.Window):
    """
    Main application window. Routes controller button events to the
    active view for menu navigation. GameView handles its own input
    via InputManager polling.
    """

    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.BLACK)
        self.menu_controllers = []
        self._menu_handler_view = None
        self.sound = SoundManager()

    def setup(self):
        """Connect all controllers and show the title screen."""
        controllers = arcade.get_controllers()
        for c in controllers[:4]:
            try:
                c.open()
            except Exception:
                pass
            self.menu_controllers.append(c)

        # Use a single bridge object that forwards button presses to
        # whatever view is current. This avoids push/remove handler churn.
        bridge = self
        for c in self.menu_controllers:
            c.push_handlers(
                on_button_press=self._on_menu_button_press
            )

        self.show_view(TitleView())

    def _on_menu_button_press(self, controller, button):
        """Forward button presses to the active view if it's a menu view."""
        from chasma.views.game_view import GameView
        view = self.current_view
        if view and not isinstance(view, GameView):
            if hasattr(view, 'on_button_press'):
                view.on_button_press(controller, button)
