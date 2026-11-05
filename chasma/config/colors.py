try:
    import arcade
    _HAS_ARCADE = True
except ImportError:
    arcade = None
    _HAS_ARCADE = False


class ChasmaColors:
    GRID_BLUE = arcade.color.AZURE if _HAS_ARCADE else (240, 255, 255)
    PLAYER1_YELLOW = arcade.color.YELLOW if _HAS_ARCADE else (255, 255, 0)
    PLAYER2_RED = arcade.color.RED if _HAS_ARCADE else (255, 0, 0)
    PLAYER3_BLUE = arcade.color.BLUE if _HAS_ARCADE else (0, 0, 255)
    PLAYER4_GREEN = arcade.color.GREEN if _HAS_ARCADE else (0, 128, 0)
    SHIP_GRAY = arcade.color.GRAY if _HAS_ARCADE else (128, 128, 128)
    HOLLOWSTAR_DISC  = (210, 140, 40)
    HOLLOWSTAR_GLOW  = (180, 220, 255)
