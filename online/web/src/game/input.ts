/**
 * Browser Keyboard + HTML5 Gamepad API Input Manager.
 * Mirrors `chasma/systems/input_manager.py` and `chasma/config/controls.py`.
 */

import { CHASMA_CONFIG } from "../config/generated_config";

export interface LocalInputState {
  rotation: number; // -1.0 (left) to +1.0 (right)
  thrust: number;   // 0.0 to 1.0
  fire: boolean;
}

export class WebInputManager {
  private keysPressed = new Set<string>();
  public activeGamepadName: string | null = null;
  private onDebugToggle?: () => void;
  private onMuteToggle?: () => void;
  private onActionConfirm?: () => void;

  constructor(callbacks?: {
    onDebugToggle?: () => void;
    onMuteToggle?: () => void;
    onActionConfirm?: () => void;
  }) {
    this.onDebugToggle = callbacks?.onDebugToggle;
    this.onMuteToggle = callbacks?.onMuteToggle;
    this.onActionConfirm = callbacks?.onActionConfirm;

    window.addEventListener("keydown", this.handleKeyDown);
    window.addEventListener("keyup", this.handleKeyUp);
    window.addEventListener("blur", this.handleBlur);
    window.addEventListener("gamepadconnected", (e: GamepadEvent) => {
      this.activeGamepadName = e.gamepad.id;
    });
    window.addEventListener("gamepaddisconnected", () => {
      this.activeGamepadName = null;
    });
  }

  public destroy(): void {
    window.removeEventListener("keydown", this.handleKeyDown);
    window.removeEventListener("keyup", this.handleKeyUp);
    window.removeEventListener("blur", this.handleBlur);
  }

  private handleKeyDown = (e: KeyboardEvent): void => {
    // Do not hijack keys if typing in a text input (e.g., callsign or room code)
    const tag = (e.target as HTMLElement | null)?.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA") return;

    if (e.code === "F1") {
      e.preventDefault();
      this.onDebugToggle?.();
      return;
    }
    if (e.code === "KeyM") {
      this.onMuteToggle?.();
      return;
    }
    if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Space"].includes(e.code)) {
      e.preventDefault();
    }
    if (!this.keysPressed.has(e.code) && (e.code === "Space" || e.code === "Enter")) {
      this.onActionConfirm?.();
    }
    this.keysPressed.add(e.code);
  };

  private handleKeyUp = (e: KeyboardEvent): void => {
    this.keysPressed.delete(e.code);
  };

  private handleBlur = (): void => {
    this.keysPressed.clear();
  };

  public poll(): LocalInputState {
    const state: LocalInputState = {
      rotation: 0.0,
      thrust: 0.0,
      fire: false,
    };

    // 1. Poll Keyboard
    const left = this.keysPressed.has("ArrowLeft") || this.keysPressed.has("KeyA");
    const right = this.keysPressed.has("ArrowRight") || this.keysPressed.has("KeyD");
    if (left && !right) state.rotation = -1.0;
    else if (right && !left) state.rotation = 1.0;

    if (this.keysPressed.has("ArrowUp") || this.keysPressed.has("KeyW")) {
      state.thrust = 1.0;
    }

    if (this.keysPressed.has("Space")) {
      state.fire = true;
    }

    // 2. Poll HTML5 Gamepad API (overrides if active input detected)
    const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
    for (const gp of gamepads) {
      if (!gp || !gp.connected) continue;
      if (!this.activeGamepadName) {
        this.activeGamepadName = gp.id;
      }

      const stickDeadzone = CHASMA_CONFIG.controls.STICK_DEADZONE;
      const triggerDeadzone = CHASMA_CONFIG.controls.TRIGGER_DEADZONE;

      // Left stick X (axis 0) or D-Pad Left/Right (buttons 14/15)
      const lx = gp.axes[0] ?? 0;
      if (Math.abs(lx) > stickDeadzone) {
        state.rotation = Math.max(-1.0, Math.min(1.0, lx));
      } else if (gp.buttons[14]?.pressed) {
        state.rotation = -1.0;
      } else if (gp.buttons[15]?.pressed) {
        state.rotation = 1.0;
      }

      // Right trigger (button 7) or Right Bumper (button 5)
      const rt = gp.buttons[7]?.value ?? 0;
      if (rt > triggerDeadzone) {
        state.thrust = Math.max(state.thrust, Math.min(1.0, rt));
      } else if (gp.buttons[5]?.pressed) {
        state.thrust = 1.0;
      }

      // A / Cross button (button 0) for Blaster Fire
      if (gp.buttons[0]?.pressed) {
        state.fire = true;
        this.onActionConfirm?.();
      }
      break;
    }

    return state;
  }
}
