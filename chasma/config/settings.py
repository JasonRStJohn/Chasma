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
ARENA_MARGIN = 40
ARENA_LEFT = ARENA_MARGIN
ARENA_RIGHT = SCREEN_WIDTH - ARENA_MARGIN
ARENA_BOTTOM = ARENA_MARGIN
ARENA_TOP = SCREEN_HEIGHT - ARENA_MARGIN
GRID_SPACING = 64
WALL_THICKNESS = 2

# --- Hollowstar ---
HOLLOWSTAR_SPEED          = 0.9
HOLLOWSTAR_WANDER_STRENGTH = 0.03
HOLLOWSTAR_SPIN_SPEED     = 3
HOLLOWSTAR_CENTER_PULL    = 0.005

# Visual
HOLLOWSTAR_DISC_OUTER     = 42
HOLLOWSTAR_DISC_INNER     = 22
HOLLOWSTAR_GLOW_RADIUS    = 26
HOLLOWSTAR_SINGULARITY    = 9

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
# Spawn positions: corners of the arena with some offset
PLAYER_SPAWNS = [
    (ARENA_LEFT + 80, ARENA_BOTTOM + 80),
    (ARENA_RIGHT - 80, ARENA_TOP - 80),
    (ARENA_RIGHT - 80, ARENA_BOTTOM + 80),
    (ARENA_LEFT + 80, ARENA_TOP - 80),
]

# --- Blaster ---
BLASTER_SPEED = 6.0
BLASTER_LENGTH = 12
BLASTER_WIDTH = 3
BLASTER_LIFETIME = 120       # frames before disappearing
BLASTER_KNOCKBACK = 4.0      # velocity imparted on hit
BLASTER_COOLDOWN = 45        # frames between shots
BLASTER_HIT_RADIUS = 14      # collision radius with players

# --- Thrust Flame ---
FLAME_MIN_LENGTH = 5
FLAME_MAX_LENGTH = 18
FLAME_WIDTH = 6
