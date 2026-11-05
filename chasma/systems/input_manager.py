try:
    import arcade
except ImportError:
    arcade = None

from chasma.config.settings import *
from chasma.config.controls import *
from chasma.core.simulation import InputState


class InputManager:
    """
    Manages all input sources and produces an InputState per player each frame.
    Uses polling for controllers and key-tracking for keyboard.
    """

    def __init__(self, controllers):
        """
        controllers: list of opened arcade controller objects.
        If empty, player 1 uses keyboard. Otherwise each controller = one player.
        """
        self.controllers = controllers
        self.use_keyboard = len(controllers) == 0
        self.num_players = max(1, len(controllers))

        # Keyboard state tracking
        self.keys_pressed = set()

    def on_key_press(self, key):
        """Track key presses."""
        self.keys_pressed.add(key)

    def on_key_release(self, key):
        """Track key releases."""
        self.keys_pressed.discard(key)

    def get_states(self):
        """
        Poll all input sources and return a list of InputState,
        one per player.
        """
        states = []

        if self.use_keyboard:
            states.append(self._poll_keyboard())
        else:
            for controller in self.controllers:
                states.append(self._poll_controller(controller))

        return states

    def _poll_keyboard(self):
        """Build InputState from keyboard."""
        state = InputState()

        if arcade.key.LEFT in self.keys_pressed:
            state.rotation = -1.0
        elif arcade.key.RIGHT in self.keys_pressed:
            state.rotation = 1.0

        if arcade.key.UP in self.keys_pressed:
            state.thrust = 1.0

        if arcade.key.SPACE in self.keys_pressed:
            state.fire = True

        if arcade.key.ESCAPE in self.keys_pressed:
            state.pause = True

        return state

    def _poll_controller(self, controller):
        """Build InputState from a controller's current state."""
        state = InputState()

        # Left stick X for rotation
        if abs(controller.leftx) > STICK_DEADZONE:
            state.rotation = controller.leftx

        # Right trigger for thrust
        rt = controller.righttrigger
        if rt is not None and rt > TRIGGER_DEADZONE:
            state.thrust = rt

        # A button for fire (future)
        if controller.a:
            state.fire = True

        # Start for pause
        if controller.start:
            state.pause = True

        return state

    def check_any_pause(self):
        """Check if any player is pressing pause. Used to avoid repeated triggers."""
        if self.use_keyboard:
            return arcade.key.ESCAPE in self.keys_pressed
        return any(c.start for c in self.controllers)
