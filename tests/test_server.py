"""
Integration tests for Milestone 2 (`online/server/` FastAPI & WebSocket Room Coordinator).
"""

import json
import unittest
from fastapi.testclient import TestClient

from online.server.app import app


class TestChasmaOnlineServer(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_health_and_config_endpoints(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["onnx_loaded"])

        cfg_res = self.client.get("/api/config")
        self.assertEqual(cfg_res.status_code, 200)
        cfg = cfg_res.json()
        self.assertEqual(cfg["screen"]["SCREEN_WIDTH"], 1920)
        self.assertIn("GRAVITY_STRENGTH", cfg["tuning"])

    def test_create_room_endpoint(self):
        res = self.client.post("/api/rooms")
        self.assertEqual(res.status_code, 200)
        room_code = res.json()["room"]
        self.assertEqual(len(room_code), 4)

    def test_serves_built_spa_and_invite_url(self):
        res = self.client.get("/?room=K7X9")
        self.assertEqual(res.status_code, 200)
        self.assertIn("CHASMA", res.text)

    def test_multi_client_websocket_slots_and_hot_swap_ai(self):
        with self.client.websocket_connect("/ws/TEST?name=Jason") as ws1:
            welcome1 = json.loads(ws1.receive_text())
            self.assertEqual(welcome1["t"], "welcome")
            self.assertEqual(welcome1["room"], "TEST")
            self.assertEqual(welcome1["slot"], 0)

            # Second player connects to same room URL -> gets slot 1
            with self.client.websocket_connect("/ws/TEST?name=Friend") as ws2:
                welcome2 = json.loads(ws2.receive_text())
                self.assertEqual(welcome2["t"], "welcome")
                self.assertEqual(welcome2["slot"], 1)

                # Send input packet from Player 1
                ws1.send_text(json.dumps({"t": "i", "seq": 42, "rot": 1.0, "thr": 1.0, "fire": 1}))

                # Receive state broadcast on ws2 (guaranteed to be emitted after ws2 joined)
                state_msg = json.loads(ws2.receive_text())
                self.assertEqual(state_msg["t"], "s")
                self.assertEqual(len(state_msg["p"]), 4)
                # Slot 0 and Slot 1 are human (is_ai == 0); Slots 2 and 3 are AI (is_ai == 1)
                self.assertEqual(state_msg["p"][0][10], 0)
                self.assertEqual(state_msg["p"][0][11], "Jason")
                self.assertEqual(state_msg["p"][1][10], 0)
                self.assertEqual(state_msg["p"][1][11], "Friend")
                self.assertEqual(state_msg["p"][2][10], 1)
                self.assertEqual(state_msg["p"][3][10], 1)

                # Ping/pong check
                ws1.send_text(json.dumps({"t": "cmd", "action": "ping", "ts": 123456}))

            # After ws2 disconnects, Slot 1 should immediately revert to AI backfill
            from online.server.app import room_manager
            room = room_manager.get_or_create_room("TEST")
            self.assertTrue(room.sim.players[1].is_ai)


if __name__ == "__main__":
    unittest.main()
