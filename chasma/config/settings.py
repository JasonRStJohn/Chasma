# Game constants

# --- Screen ---
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
SCREEN_TITLE = "Chasma"

# --- Physics and Movement ---
# Controls how much the ship rotates per key press
ROTATION_SPEED = 5
# Controls how much force is applied when thrusting
THRUST_FORCE = 0.15
# A factor to slow the ship down over time (simulates friction)
DRAG_COEFFICIENT = 0.995

# --- Arena ---
ARENA_MARGIN_X = 260
ARENA_MARGIN_Y = 140
ARENA_LEFT = ARENA_MARGIN_X
ARENA_RIGHT = SCREEN_WIDTH - ARENA_MARGIN_X
ARENA_BOTTOM = ARENA_MARGIN_Y
ARENA_TOP = SCREEN_HEIGHT - ARENA_MARGIN_Y
ARENA_MARGIN = ARENA_MARGIN_Y
GRID_SPACING = 64
WALL_THICKNESS = 2

# --- Hollowstar ---
HOLLOWSTAR_SPEED          = 0.9
HOLLOWSTAR_WANDER_STRENGTH = 0.03
HOLLOWSTAR_SPIN_SPEED     = 3
HOLLOWSTAR_CENTER_PULL    = 0.005

# Visual
HOLLOWSTAR_DISC_OUTER     = 56
HOLLOWSTAR_DISC_INNER     = 28
HOLLOWSTAR_GLOW_RADIUS    = 34
HOLLOWSTAR_SINGULARITY    = 12

# Gravity zones
GRAVITY_STRENGTH          = 3200.0
GRAVITY_OUTER_RADIUS      = 420
GRAVITY_INNER_RADIUS      = 52
GRAVITY_MIN_DIST          = 30

# Spiral death sequence
SPIRAL_DURATION           = 50
SPIRAL_FORCE_MULTIPLIER   = 8.0
SPIRAL_SPIN_SPEED         = 15
MAX_SPIRAL_SPEED          = 10.0   # prevents velocity overshoot
RESPAWN_DELAY             = 90     # frames invisible before respawn (~1.5s)

# Grid warp
GRID_WARP_SEGMENTS        = 12
GRID_WARP_STRENGTH        = 1800
GRID_WARP_FALLOFF         = 60

# --- Player ---
PLAYER_LIVES = 3
PLAYER_COLORS = ["PLAYER1_YELLOW", "PLAYER2_RED", "PLAYER3_BLUE", "PLAYER4_GREEN"]
# Live-tunable ship scale and collision physics
SHIP_SCALE = 1.2
SHIP_COLLISION_STRENGTH = 1.2

# Spawn positions: corners of the arena with offset
PLAYER_SPAWNS = [
    (ARENA_LEFT + 120, ARENA_BOTTOM + 120),
    (ARENA_RIGHT - 120, ARENA_TOP - 120),
    (ARENA_RIGHT - 120, ARENA_BOTTOM + 120),
    (ARENA_LEFT + 120, ARENA_TOP - 120),
]

# --- Blaster ---
BLASTER_SPEED = 8.0
BLASTER_LENGTH = 20
BLASTER_WIDTH = 5
BLASTER_LIFETIME = 120       # frames before disappearing
BLASTER_KNOCKBACK = 5.0      # velocity imparted on hit
BLASTER_COOLDOWN = 45        # frames between shots
BLASTER_HIT_RADIUS = 24      # collision radius with players

# --- Thrust Flame ---
FLAME_MIN_LENGTH = 10
FLAME_MAX_LENGTH = 36
FLAME_WIDTH = 12
