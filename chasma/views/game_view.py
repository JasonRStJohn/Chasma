import math

import arcade

from chasma.config.settings import *
from chasma.config import tuning
from chasma.config.colors import ChasmaColors
from chasma.core.arena import Arena
from chasma.entities.hollowstar import Hollowstar
from chasma.entities.player import Player
from chasma.systems.debug_tuner import DebugTuner
from chasma.systems.input_manager import InputManager


# Map color names to actual colors
_COLOR_MAP = {
    "PLAYER1_YELLOW": ChasmaColors.PLAYER1_YELLOW,
    "PLAYER2_RED": ChasmaColors.PLAYER2_RED,
    "PLAYER3_BLUE": ChasmaColors.PLAYER3_BLUE,
    "PLAYER4_GREEN": ChasmaColors.PLAYER4_GREEN,
}


class GameView(arcade.View):
    """Main gameplay view — supports 1-4 players."""

    def __init__(self):
        super().__init__()
        self.arena = None
        self.hollowstar = None
        self.players = []
        self.projectiles = []
        self.input_manager = None
        self.pause_held = False
        self.debug_tuner = DebugTuner()

    def setup(self):
        """Set up the game and initialize variables."""
        self.arena = Arena()
        self.projectiles = []

        # Use the controllers already opened by ChasmaGame
        self.input_manager = InputManager(self.window.menu_controllers)
        num_players = self.input_manager.num_players

        # --- Create players ---
        self.players = []
        for i in range(num_players):
            color_name = PLAYER_COLORS[i]
            color = _COLOR_MAP[color_name]
            spawn_x, spawn_y = PLAYER_SPAWNS[i]
            player = Player(
                player_color=color,
                center_x=spawn_x,
                center_y=spawn_y,
            )
            self.players.append(player)

        # --- Create Hollowstar in the center ---
        self.hollowstar = Hollowstar(
            center_x=SCREEN_WIDTH / 2,
            center_y=SCREEN_HEIGHT / 2,
        )

        # HUD text objects — one per player
        self.lives_texts = []
        for i, player in enumerate(self.players):
            text = arcade.Text(
                f"P{i+1}: {player.lives}",
                ARENA_LEFT + 10 + i * 100, ARENA_TOP + 10,
                player.player_color, font_size=14,
            )
            self.lives_texts.append(text)

        self.pause_held = False

    def on_show_view(self):
        arcade.set_background_color(arcade.color.BLACK)

    def on_draw(self):
        self.clear()

        self.arena.draw(self.hollowstar.center_x, self.hollowstar.center_y)
        self.hollowstar.draw()

        for proj in self.projectiles:
            proj.draw()

        for player in self.players:
            player.draw()

        # HUD
        for i, player in enumerate(self.players):
            self.lives_texts[i].text = f"P{i+1}: OUT" if player.lives <= 0 else f"P{i+1}: {player.lives}"
            self.lives_texts[i].draw()

        self.debug_tuner.draw_overlay(self.hollowstar.center_x, self.hollowstar.center_y)

    def on_update(self, delta_time):
        # --- Input ---
        input_states = self.input_manager.get_states()

        # Check for pause (with edge detection so it doesn't repeat)
        any_pause = any(s.pause for s in input_states)
        if any_pause and not self.pause_held:
            self.pause_held = True
            from chasma.views.pause_view import PauseView
            self.window.show_view(PauseView(self))
            return
        if not any_pause:
            self.pause_held = False

        # --- Gravity field ---
        for player in self.players:
            if not player.alive or player.spiraling:
                continue
            dx = self.hollowstar.center_x - player.center_x
            dy = self.hollowstar.center_y - player.center_y
            distance = math.hypot(dx, dy)
            if distance < tuning.GRAVITY_OUTER_RADIUS:
                force = tuning.GRAVITY_STRENGTH / max(distance, tuning.GRAVITY_MIN_DIST) ** 2
                player.velocity_x += (dx / distance) * force
                player.velocity_y += (dy / distance) * force

        # Apply input and update players
        for i, player in enumerate(self.players):
            # Respawn countdown — player is invisible until timer expires
            if not player.alive and player.respawn_timer >= 0:
                player.respawn_timer -= 1
                if player.respawn_timer < 0:
                    spawn_x, spawn_y = PLAYER_SPAWNS[i]
                    player.respawn(spawn_x, spawn_y)
                    player.alive = True

            if player.alive and i < len(input_states):
                player.apply_input(input_states[i])
            player.update()
            if player.alive and not player.spiraling:
                self.arena.bounce(player, dampening=0.5)

            # --- Fire blasters ---
            proj = player.try_fire()
            if proj:
                self.projectiles.append(proj)
                self.window.sound.play("fire")

        # --- Spiral death sequence ---
        for i, player in enumerate(self.players):
            if not player.alive:
                continue

            dx = self.hollowstar.center_x - player.center_x
            dy = self.hollowstar.center_y - player.center_y
            distance = math.hypot(dx, dy)

            if player.spiraling:
                # Pull hard toward center during spiral
                force = tuning.GRAVITY_STRENGTH * tuning.SPIRAL_FORCE_MULTIPLIER / max(distance, tuning.GRAVITY_MIN_DIST) ** 2
                player.velocity_x += (dx / max(distance, 1)) * force
                player.velocity_y += (dy / max(distance, 1)) * force
                # Cap velocity so the ship doesn't overshoot the Hollowstar
                speed = math.hypot(player.velocity_x, player.velocity_y)
                if speed > tuning.MAX_SPIRAL_SPEED:
                    player.velocity_x = (player.velocity_x / speed) * tuning.MAX_SPIRAL_SPEED
                    player.velocity_y = (player.velocity_y / speed) * tuning.MAX_SPIRAL_SPEED
                player.spiral_timer -= 1
                if player.spiral_timer <= 0:
                    player.spiraling = False
                    player.velocity_x = 0
                    player.velocity_y = 0
                    player.alive = False   # ship disappears into the Hollowstar
                    eliminated = player.die()
                    self.window.sound.play("death")
                    if not eliminated:
                        player.respawn_timer = RESPAWN_DELAY
            elif distance < tuning.GRAVITY_INNER_RADIUS:
                player.begin_spiral()
                self.window.sound.play("suck")

        # --- Update projectiles ---
        for proj in self.projectiles:
            proj.update()
            self.arena.bounce(proj, dampening=1.0)

        # Remove dead projectiles (timed out)
        self.projectiles = [p for p in self.projectiles if p.alive]

        # --- Projectile-player collisions ---
        for proj in self.projectiles:
            for player in self.players:
                if proj.check_hit(player):
                    # Apply knockback in the direction the projectile is traveling
                    angle_rad = math.radians(proj.angle)
                    player.velocity_x += math.sin(angle_rad) * BLASTER_KNOCKBACK
                    player.velocity_y += math.cos(angle_rad) * BLASTER_KNOCKBACK
                    proj.kill()
                    self.window.sound.play("hit")
                    break

        # Update Hollowstar
        self.hollowstar.update()
        self.arena.bounce(self.hollowstar, dampening=1.0)

        # --- Check for game over ---
        # A player is still in the match if they have lives remaining (even mid-respawn)
        surviving = [p for p in self.players if p.lives > 0]
        if len(self.players) == 1 and len(surviving) == 0:
            # Single player mode — game over
            from chasma.views.game_over_view import GameOverView
            self.window.sound.play("game_over")
            self.window.show_view(GameOverView())
        elif len(self.players) > 1 and len(surviving) <= 1:
            # Multiplayer — last ship standing (or all dead)
            from chasma.views.game_over_view import GameOverView
            winner = surviving[0] if surviving else None
            self.window.sound.play("win" if winner else "game_over")
            self.window.show_view(GameOverView(winner))

    # --- Keyboard input forwarding ---
    def on_key_press(self, key, modifiers):
        if self.debug_tuner.on_key_press(key, modifiers):
            return
        self.input_manager.on_key_press(key)

    def on_key_release(self, key, modifiers):
        self.input_manager.on_key_release(key)
