import json
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.local_player_bridge import LocalPlayerBridge, PlayerBridgeError


class LocalPlayerBridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = LocalPlayerBridge(port=0, command_timeout=2)
        self.bridge.start()

    def tearDown(self):
        self.bridge.stop()

    def get_json(self, path):
        with urllib.request.urlopen(self.bridge.url.rstrip("/") + path, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def post_json(self, path, payload):
        request = urllib.request.Request(
            self.bridge.url.rstrip("/") + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            data = response.read()
            return response.status, (json.loads(data.decode("utf-8")) if data else {})

    def test_player_page_is_served(self):
        with urllib.request.urlopen(self.bridge.url, timeout=2) as response:
            html = response.read().decode("utf-8")
        self.assertEqual(response.status, 200)
        self.assertIn("https://www.youtube.com/iframe_api", html)
        self.assertIn("/api/next-command", html)

    def test_rejects_non_loopback_bind(self):
        with self.assertRaises(ValueError):
            LocalPlayerBridge(host="0.0.0.0")

    def test_open_video_requires_valid_youtube_id(self):
        with self.assertRaises(ValueError):
            self.bridge.open_video("not-an-id")

    def test_status_endpoint_reports_unconnected_initial_state(self):
        status, body = self.get_json("/api/status")
        self.assertEqual(status, 200)
        self.assertFalse(body["connected"])

    def test_open_video_dispatch_and_browser_acknowledgment(self):
        result_box = {}

        def open_in_agent_thread():
            try:
                result_box["result"] = self.bridge.open_video("abcdefghijk")
            except Exception as exc:  # result inspected by test thread
                result_box["error"] = exc

        caller = threading.Thread(target=open_in_agent_thread)
        caller.start()

        deadline = time.monotonic() + 1
        command = None
        while time.monotonic() < deadline and command is None:
            _, body = self.get_json("/api/next-command")
            command = body["command"]
            if command is None:
                time.sleep(0.01)

        self.assertIsNotNone(command)
        self.assertEqual(command["operation"], "open")
        self.assertEqual(command["video_id"], "abcdefghijk")

        status, _ = self.post_json(
            "/api/events",
            {
                "type": "command_result",
                "command_id": command["command_id"],
                "success": True,
                "video_id": "abcdefghijk",
                "player_state": "cued",
                "message": "Video loaded and cued",
            },
        )
        self.assertEqual(status, 202)
        caller.join(timeout=1)
        self.assertFalse(caller.is_alive())
        self.assertNotIn("error", result_box)
        self.assertTrue(result_box["result"]["success"])
        self.assertEqual(self.bridge.status()["video_id"], "abcdefghijk")

    def test_manual_open_endpoint_queues_command(self):
        status, body = self.post_json("/api/manual-open", {"video_id": "abcdefghijk"})
        self.assertEqual(status, 202)
        self.assertTrue(body["queued"])
        _, command_body = self.get_json("/api/next-command")
        self.assertEqual(command_body["command"]["video_id"], "abcdefghijk")

    def test_command_times_out_if_browser_does_not_acknowledge(self):
        with self.assertRaises(PlayerBridgeError):
            self.bridge.open_video("abcdefghijk", timeout=0.01)


if __name__ == "__main__":
    unittest.main()
