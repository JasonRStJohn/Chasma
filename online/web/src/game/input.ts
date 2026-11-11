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

  private isPlayStationController(gp: Gamepad): boolean {
    const id = gp.id.toLowerCase();
    return (
      id.includes("054c") ||
      id.includes("playstation") ||
      id.includes("dualshock") ||
      id.includes("dualsense") ||
      id.includes("wireless controller")
    );
  }

  /**
   * Read the analog Right Trigger (R2 / RT) value normalized to [0.0, 1.0].
   *
   * On PC, PlayStation controllers (DualShock 4 / DualSense) over DirectInput / Raw HID
   * often report R2 in two places simultaneously:
   *  - `gp.buttons[7]` (DirectInput Button 7): a digital threshold bit (0 or 1), which
   *    causes `gp.buttons[7].value` to jump from 0.0 straight to 1.0 when pressed.
   *  - `gp.axes[4]` (or `gp.axes[5]`): the true 8-bit analog trigger axis in [-1.0, +1.0],
   *    where -1.0 is released and +1.0 is fully depressed.
   */
  private readRightTrigger(gp: Gamepad): number {
    const btn7 = gp.buttons[7];
    const btnVal = btn7?.value ?? 0;

    // If the browser's standard mapping is already providing fractional analog values on button 7, use it
    if (btnVal > 0 && btnVal < 1) {
      return btnVal;
    }

    // For PlayStation or non-standard controllers on PC, check the analog trigger axis in `gp.axes`
    if (this.isPlayStationController(gp) || gp.mapping !== "standard") {
      // On DualShock 4 / DualSense PC HID reports:
      // axes[0]=LX, axes[1]=LY, axes[2]=RX, axes[3]=L2, axes[4]=R2, axes[5]=RY
      // (Some drivers order axes[2]=RX, axes[3]=RY, axes[4]=L2, axes[5]=R2)
      const r2AxisIndex = gp.axes.length >= 5 ? 4 : -1;
      if (r2AxisIndex !== -1) {
        const rawAxis = gp.axes[r2AxisIndex];
        if (typeof rawAxis === "number" && !Number.isNaN(rawAxis)) {
          // Convert [-1.0, +1.0] range (-1.0 at rest, +1.0 full press) -> [0.0, 1.0]
          // Note: Before first press, some browsers initialize unpressed axes to 0.0 until moved;
          // guard against false 50% thrust when button 7 is not pressed and axis is 0.0 at rest.
          if (rawAxis === 0 && !btn7?.pressed) {
            return 0.0;
          }
          return Math.max(0.0, Math.min(1.0, (rawAxis + 1.0) / 2.0));
        }
      }
    }

    return btnVal;
  }

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
      const isPS = this.isPlayStationController(gp) && gp.mapping !== "standard";

      // Left stick X (axis 0) or D-Pad Left/Right (buttons 14/15)
      const lx = gp.axes[0] ?? 0;
      if (Math.abs(lx) > stickDeadzone) {
        state.rotation = Math.max(-1.0, Math.min(1.0, lx));
      } else if (gp.buttons[14]?.pressed) {
        state.rotation = -1.0;
      } else if (gp.buttons[15]?.pressed) {
        state.rotation = 1.0;
      }

      // Right trigger (analog R2 / RT) or Right Bumper (R1 / RB, button 5)
      const rt = this.readRightTrigger(gp);
      if (rt > triggerDeadzone) {
        state.thrust = Math.max(state.thrust, Math.min(1.0, rt));
      } else if (gp.buttons[5]?.pressed) {
        state.thrust = 1.0;
      }

      // Cross / A button for Blaster Fire:
      // Standard mapping places Cross/A at buttons[0], whereas raw DirectInput on PlayStation
      // places Square at buttons[0] and Cross at buttons[1]. Support buttons[0] (and buttons[1] on raw PS).
      const firePressed = isPS
        ? Boolean(gp.buttons[1]?.pressed || gp.buttons[0]?.pressed)
        : Boolean(gp.buttons[0]?.pressed);
      if (firePressed) {
        state.fire = true;
        this.onActionConfirm?.();
      }
      break;
    }

    return state;
  }
}
