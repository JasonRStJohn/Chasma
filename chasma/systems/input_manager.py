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
        rt = self._read_right_trigger(controller)
        if rt > TRIGGER_DEADZONE:
            state.thrust = rt

        # A button for fire (future)
        if controller.a:
            state.fire = True

        # Start for pause
        if controller.start:
            state.pause = True

        return state

    @staticmethod
    def _read_right_trigger(controller) -> float:
        """
        Read analog right trigger (R2 / RT) normalized to [0.0, 1.0].

        On Windows DirectInput, PlayStation controllers (DualShock 4 / DualSense)
        expose R2 both as a digital threshold button (`_button_controls[7]`) and
        as an analog axis (`ry` / `_axis_controls[4]`). If the mapping binds
        `righttrigger` to the button (`b7`) or if `_axis_controls` ordering shifts,
        fall back to reading the raw `ry` trigger axis or digital R2 button.
        """
        rt = getattr(controller, "righttrigger", 0.0)
        if isinstance(rt, (int, float)) and not isinstance(rt, bool) and rt > 0.0:
            return float(rt)

        # If `righttrigger` was bound to a digital Button (True/False) or stayed 0.0
        # while the analog trigger axis (`ry` at index 4 on PS DirectInput) is active:
        axis_controls = getattr(controller, "_axis_controls", None)
        name = (getattr(controller, "name", "") or "").lower()
        is_ps = any(k in name for k in ("ps4", "ps5", "playstation", "dualshock", "dualsense", "wireless controller"))
        if is_ps and axis_controls and len(axis_controls) > 4:
            ctrl = axis_controls[4]
            span = getattr(ctrl, "max", 0) - getattr(ctrl, "min", 0)
            val = getattr(ctrl, "value", None)
            if span > 0 and val is not None:
                norm = (val - ctrl.min) / span
                if norm > 0.0:
                    return max(0.0, min(1.0, float(norm)))

        if rt:
            return 1.0
        return 0.0

    def check_any_pause(self):
        """Check if any player is pressing pause. Used to avoid repeated triggers."""
        if self.use_keyboard:
            return arcade.key.ESCAPE in self.keys_pressed
        return any(c.start for c in self.controllers)
