"""
Unit and headless verification tests for Milestone 1 (`ChasmaSimulation` & Sync Pipeline).
"""

import math
import sys
import time
import unittest
from pathlib import Path

from chasma.config import settings, tuning
from chasma.core.simulation import (
    ChasmaSimulation,
    InputState,
    ShipState,
    HollowstarState,
    ProjectileState,
)
from online.scripts.sync_online import get_runtime_config, generate_typescript_config


class TestChasmaSimulation(unittest.TestCase):

    def setUp(self):
        self.sim = ChasmaSimulation(num_human_players=1)

    def test_initial_setup_4_players_and_ai_backfill(self):
        self.assertEqual(len(self.sim.players), 4)
        self.assertFalse(self.sim.players[0].is_ai)
        self.assertTrue(self.sim.players[1].is_ai)
        self.assertTrue(self.sim.players[2].is_ai)
        self.assertTrue(self.sim.players[3].is_ai)
        self.assertIsNotNone(self.sim.hollowstar)

    def test_gravity_pull_inside_outer_radius(self):
        p0 = self.sim.players[0]
        # Place player 150px to the left of the Hollowstar (inside GRAVITY_OUTER_RADIUS)
        p0.center_x = self.sim.hollowstar.center_x - 150.0
        p0.center_y = self.sim.hollowstar.center_y
        p0.velocity_x = 0.0
        p0.velocity_y = 0.0

        self.sim.step({0: InputState()})
        # Should be pulled toward the Hollowstar (+X direction)
        self.assertGreater(p0.velocity_x, 0.0)

    def test_spiral_death_and_respawn_lifecycle(self):
        p0 = self.sim.players[0]
        initial_lives = p0.lives
        # Place player inside GRAVITY_INNER_RADIUS
        p0.center_x = self.sim.hollowstar.center_x + 10.0
        p0.center_y = self.sim.hollowstar.center_y

        res = self.sim.step({0: InputState()})
        self.assertTrue(p0.spiraling)
        self.assertIn("suck", res.events)

        # Advance through spiral duration
        died_event_seen = False
        for _ in range(int(tuning.SPIRAL_DURATION) + 2):
            # Keep Hollowstar close so spiral completes cleanly
            self.sim.hollowstar.center_x = p0.center_x
            self.sim.hollowstar.center_y = p0.center_y
            step_res = self.sim.step({0: InputState()})
            if "death" in step_res.events:
                died_event_seen = True
                break

        self.assertTrue(died_event_seen)
        self.assertEqual(p0.lives, initial_lives - 1)
        self.assertFalse(p0.alive)
        self.assertGreaterEqual(p0.respawn_timer, 0)

        # Advance through respawn timer
        for _ in range(settings.RESPAWN_DELAY + 2):
            self.sim.step({0: InputState()})
        self.assertTrue(p0.alive)

    def test_elastic_ship_to_ship_collision(self):
        p0 = self.sim.players[0]
        p1 = self.sim.players[1]
        p1.is_ai = False

        # Place ships overlapping and moving toward each other along X
        p0.center_x = 600.0
        p0.center_y = 500.0
        p0.velocity_x = 3.0
        p0.velocity_y = 0.0

        p1.center_x = 620.0
        p1.center_y = 500.0
        p1.velocity_x = -3.0
        p1.velocity_y = 0.0

        res = self.sim.step({0: InputState(), 1: InputState()})
        self.assertIn("hit", res.events)
        # Velocities should have reversed after elastic collision
        self.assertLess(p0.velocity_x, 0.0)
        self.assertGreater(p1.velocity_x, 0.0)

    def test_blaster_rising_edge_and_knockback(self):
        for p in self.sim.players:
            p.is_ai = False
        p0 = self.sim.players[0]
        p1 = self.sim.players[1]

        p0.center_x = 500.0
        p0.center_y = 500.0
        p0.angle = 90.0  # Facing +X (East)

        # Place p1 directly in front of p0's nose (nose_dist = 22 * 2.0 = 44 -> 544)
        p1.center_x = 600.0
        p1.center_y = 500.0
        p1.velocity_x = 0.0

        # Frame 1: press fire -> spawns projectile
        res1 = self.sim.step({0: InputState(fire=True), 1: InputState()})
        self.assertIn("fire", res1.events)
        self.assertEqual(len(self.sim.projectiles), 1)

        # Frame 2: holding fire while cooldown > 0 should not fire again
        res2 = self.sim.step({0: InputState(fire=True), 1: InputState()})
        self.assertNotIn("fire", res2.events)

        # Step a few frames until projectile hits p1
        hit_seen = False
        for _ in range(15):
            r = self.sim.step({0: InputState(), 1: InputState()})
            if "hit" in r.events:
                hit_seen = True
                break
        self.assertTrue(hit_seen)
        self.assertGreater(p1.velocity_x, 0.0)

    def test_1000_ticks_headless_performance_and_ai(self):
        sim = ChasmaSimulation(num_human_players=0)  # All 4 slots AI
        t0 = time.perf_counter()
        for _ in range(1000):
            sim.step()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        print(f"\n[Benchmark] 1,000 4-bot ONNX simulation ticks completed in {elapsed_ms:.1f} ms")
        self.assertEqual(sim.tick, 1000)

    def test_sync_online_pipeline_generates_ts_config(self):
        cfg = get_runtime_config()
        self.assertEqual(cfg["screen"]["SCREEN_WIDTH"], 1920)
        self.assertIn("GRAVITY_STRENGTH", cfg["tuning"])
        out_path = generate_typescript_config()
        self.assertTrue(out_path.exists())


if __name__ == "__main__":
    unittest.main()
