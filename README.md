# Chasma

> **Survive the Hollowstar.** A fast-paced, top-down local multiplayer 2D space arena combat game built with Python and [Arcade](https://arcade.academy/).

---

## 🌌 Overview & The *Ebonstar* Heritage

**Chasma** is a spiritual successor and homage to the classic 1988 multiplayer Amiga title ***Ebonstar*** (developed by The Dreamers Guild, designed and programmed by Robert "Wolf" McNally, and published by MicroIllusions).

In *Ebonstar*, players engaged in high-stakes space duels orbiting a central black hole, where weapons were designed not to destroy ships directly, but to knock and shove opponents into the singularity's inescapable gravity well.

**Chasma** reimagines this arena combat mechanic:
- **The Hollowstar:** A wandering singularity at the center of the arena continuously pulls ships inward via inverse-square gravitational force and warps the spacetime grid around it.
- **Knockback Combat:** Blaster shots impart heavy kinetic recoil. Instead of whittling down hit points, your goal is to manage inertia, bounce off arena walls, and weaponize gravity and blaster momentum to shove opponents across the threshold into the Hollowstar's event horizon.
- **Spiral of Death:** Crossing the inner event horizon captures a ship in an accelerated death spiral before pulling it into the singularity.
- **Zero Audio Assets Required:** Built with a real-time procedural waveform synthesizer (sine, square, triangle, sawtooth, white noise with ADSR envelopes via Pyglet), delivering retro sound effects with zero external audio assets—lightweight enough to run on single-board computers like a Raspberry Pi.

---

## 🎮 Controls

Chasma supports 1 to 4 players simultaneously using gamepads, or 1 player on keyboard if no controllers are plugged in.

### 🕹️ Gameplay Controls

| Action | Keyboard (P1) | Controller (P1–P4) |
| :--- | :--- | :--- |
| **Rotate Ship** | `Left Arrow` / `Right Arrow` | `Left Stick (X-Axis)` |
| **Thrust** | `Up Arrow` | `Right Trigger` (Analog throttle) |
| **Fire Blaster** | `Space` | `A` Button |
| **Pause / Resume** | `Escape` | `Start` Button |

---

## 🛠️ Live Prototype Debug & Physics Tuner

Chasma includes a real-time **Debug Tuner** overlay designed for rapid prototype iteration and physics tweaking during live gameplay. Any modifications made in the tuner are automatically saved to `tuning.overrides.json` and persist across game restarts.

### ⌨️ Tuner Controls

When inside a match, use the following keys to adjust game variables in real time:

| Key | Function |
| :--- | :--- |
| **`F1`** | **Toggle Debug Overlay On/Off** |
| **`[`** / **`]`** | Select Previous / Next parameter |
| **`-`** / **`=`** | Small decrement / increment on selected parameter |
| **`_`** / **`+`** *(Shift + `-`/`=`)* | Large decrement / increment on selected parameter |
| **`F2`** | Reset selected parameter to its code default |
| **`F3`** | Print all current tuning parameters and override status to terminal |
| **`F4`** | Delete `tuning.overrides.json` and revert **all** parameters to code defaults |

### 🎯 Visual Debug HUD & Gravitational Rings

When the `F1` tuner overlay is active, debug visualizers are drawn directly in the arena around the Hollowstar:
- **Cyan Outer Ring:** The outer gravitational boundary (`GRAVITY_OUTER_RADIUS`). Ships outside this ring experience zero gravity.
- **Faint Cyan Concentric Rings:** Gravity threshold contours indicating points where gravitational pull doubles ($2\times, 4\times, 8\times$ force).
- **Red Inner Ring:** The capture event horizon (`GRAVITY_INNER_RADIUS`). Crossing this boundary initiates the inescapable death spiral sequence.

### ⚙️ Tunable Physics Variables

| Parameter | Default | Step (Small / Big) | Description |
| :--- | :---: | :---: | :--- |
| `GRAVITY_STRENGTH` | `3200.0` | `100` / `500` | Gravitational pull coefficient applied via inverse-square law ($F = \frac{G}{r^2}$). |
| `GRAVITY_OUTER_RADIUS` | `420` | `10` / `40` | Outer radius (in pixels) where the Hollowstar's gravity field begins exerting force. |
| `GRAVITY_INNER_RADIUS` | `52` | `2` / `10` | Event horizon capture radius. Crossing inside triggers the spiral death sequence. |
| `GRAVITY_MIN_DIST` | `30` | `1` / `5` | Minimum distance clamping in denominator to prevent asymptotic infinite forces near center. |
| `SPIRAL_DURATION` | `50` | `2` / `10` | Number of frames the capture death spiral lasts before ship is consumed. |
| `SPIRAL_FORCE_MULTIPLIER` | `8.0` | `0.2` / `1.0` | Inward acceleration multiplier applied to a spiraling ship. |
| `SPIRAL_SPIN_SPEED` | `15` | `0.5` / `2.0` | Angular spin speed (degrees per frame) during the death spiral animation. |
| `MAX_SPIRAL_SPEED` | `10.0` | `0.2` / `1.0` | Velocity ceiling during the death spiral to prevent the ship from overshooting the singularity. |
| `GRID_WARP_STRENGTH` | `1800` | `50` / `200` | Spacetime grid distortion strength around the Hollowstar. |
| `GRID_WARP_FALLOFF` | `60` | `2` / `10` | Falloff exponent determining how sharply grid deformation tapers with distance. |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** (Tested on Python 3.10 – 3.13)
- Windows, macOS, or Linux

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/JasonRStJohn/Chasma.git
   cd Chasma
   ```

2. **Create and activate a virtual environment (recommended):**
   ```bash
   # On Windows:
   python -m venv .venv
   .venv\Scripts\activate

   # On macOS/Linux:
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the game:**
   ```bash
   python main.py
   ```

---

## 📂 Project Structure

```
Chasma/
├── chasma/
│   ├── config/
│   │   ├── colors.py          # Color palette definitions
│   │   ├── controls.py        # Controller deadzone and input configs
│   │   ├── settings.py        # Core constants and default physics settings
│   │   └── tuning.py          # Dynamic live-tuning system & persistence
│   ├── core/
│   │   ├── arena.py           # Arena boundaries, grid rendering, warping & bounces
│   │   └── game.py            # Main application window & controller router
│   ├── entities/
│   │   ├── base_entity.py     # Base entity with velocity, rotation & manual physics
│   │   ├── hollowstar.py      # Black hole entity with accretion disc & singularity
│   │   ├── player.py          # Player ship geometry, thrusters, lives & input handling
│   │   └── projectile.py      # Blaster shots, lifetimes, and knockback collisions
│   ├── systems/
│   │   ├── debug_tuner.py     # F1 debug overlay, HUD text rendering & key handlers
│   │   ├── input_manager.py   # Multi-controller polling & keyboard abstraction
│   │   └── sound.py           # Procedural waveform synthesizer (zero audio assets)
│   └── views/
│       ├── game_over_view.py  # Match outcome & restart screen
│       ├── game_view.py       # Main simulation loop, physics & collision engine
│       ├── pause_view.py      # Pause menu overlay
│       └── title_view.py      # Animated title screen
├── main.py                    # Application entry point
├── requirements.txt           # Project dependencies
├── .gitignore                 # Git ignore rules
└── README.md                  # Project documentation
```

---

## 📜 License

This project is licensed under the MIT License.
