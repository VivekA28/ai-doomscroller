"""Loopback-only HTTP bridge for a visible YouTube IFrame Player page.

Run from the backend directory with:
    python -m src.local_player_bridge

The browser page is a separate UI. Agent code can use ``open_video`` to cue a
known YouTube video and wait for the page to acknowledge the actual player event.
"""
from __future__ import annotations

import json
import logging
import queue
import re
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_MAX_BODY_BYTES = 64 * 1024


class PlayerBridgeError(RuntimeError):
    """Raised when the visible player cannot complete a bridge operation."""


class LocalPlayerBridge:
    """Serve the player UI and deliver acknowledged commands to one browser.

    The server binds only to 127.0.0.1. It never accepts arbitrary URLs or
    browser code; commands are a small allow-listed set of player operations.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        *,
        command_timeout: float = 20.0,
        player_html_path: str | Path | None = None,
    ) -> None:
        if host != "127.0.0.1":
            raise ValueError("LocalPlayerBridge must bind to 127.0.0.1 only")
        if not 0 <= port <= 65535:
            raise ValueError("port must be between 0 and 65535")
        if command_timeout <= 0:
            raise ValueError("command_timeout must be positive")

        self.host = host
        self.port = port
        self.command_timeout = command_timeout
        self.player_html_path = Path(player_html_path) if player_html_path else (
            Path(__file__).resolve().parents[1] / "player" / "index.html"
        )
        self._commands: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=100)
        self._pending: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._status: dict[str, Any] = {
            "connected": False,
            "player_state": "not_ready",
            "video_id": None,
            "current_time": 0,
            "updated_at": time.time(),
        }
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def start(self) -> str:
        """Start serving the UI in a daemon thread and return its local URL."""
        with self._lock:
            if self._server is not None:
                return self.url
            if not self.player_html_path.is_file():
                raise FileNotFoundError(
                    f"Player UI not found: {self.player_html_path}. "
                    "Apply the player slice from the repository root."
                )
            self._server = ThreadingHTTPServer(
                (self.host, self.port), self._make_handler()
            )
            self._server.daemon_threads = True
            self.port = int(self._server.server_address[1])
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                name="doomscroller-player-http",
                daemon=True,
            )
            self._thread.start()
            logger.info("Local YouTube player available at %s", self.url)
            return self.url

    def stop(self) -> None:
        """Stop the local HTTP server and release pending callers."""
        with self._lock:
            server, thread = self._server, self._thread
            self._server = None
            self._thread = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=2)
        with self._lock:
            pending = list(self._pending.values())
            self._pending.clear()
        for item in pending:
            item["result"] = {
                "success": False,
                "message": "Local player bridge stopped",
            }
            item["event"].set()

    def open_video(self, video_id: str, *, timeout: float | None = None) -> dict[str, Any]:
        """Cue a known video in the visible page and await its player event.

        The page cues by default, preserving the user's control over playback.
        If the user enables playback in the page, subsequent open commands load
        videos for playback. A successful result means the player reported the
        video cued or playing; it does not claim that playback definitely began.
        """
        self._validate_video_id(video_id)
        return self._dispatch("open", video_id, timeout=timeout)

    def stop_playback(self, *, timeout: float | None = None) -> dict[str, Any]:
        """Ask the visible player to stop and wait for command acknowledgment."""
        return self._dispatch("stop", None, timeout=timeout)

    def status(self) -> dict[str, Any]:
        """Return the latest player status reported by the browser page."""
        with self._lock:
            return dict(self._status)

    def _dispatch(
        self, operation: str, video_id: str | None, *, timeout: float | None
    ) -> dict[str, Any]:
        if self._server is None:
            raise PlayerBridgeError("Player bridge is not running; call start() first")
        command_id = uuid.uuid4().hex
        pending = {"event": threading.Event(), "result": None}
        command = {
            "command_id": command_id,
            "operation": operation,
            "video_id": video_id,
        }
        with self._lock:
            self._pending[command_id] = pending
        try:
            self._commands.put(command, timeout=1)
        except queue.Full as exc:
            with self._lock:
                self._pending.pop(command_id, None)
            raise PlayerBridgeError("Player command queue is full") from exc

        wait_for = self.command_timeout if timeout is None else timeout
        if not pending["event"].wait(wait_for):
            with self._lock:
                self._pending.pop(command_id, None)
            raise PlayerBridgeError(
                "Timed out waiting for the visible YouTube player. "
                "Open the local player page and check that it is connected."
            )
        with self._lock:
            self._pending.pop(command_id, None)
        result = pending["result"] or {
            "success": False,
            "message": "Player command ended without a result",
        }
        if not result.get("success"):
            raise PlayerBridgeError(str(result.get("message", "Player command failed")))
        return dict(result)

    @staticmethod
    def _validate_video_id(video_id: str) -> None:
        if not isinstance(video_id, str) or not _VIDEO_ID_RE.fullmatch(video_id):
            raise ValueError("video_id must be an 11-character YouTube video ID")

    def _queue_manual_open(self, video_id: str) -> str:
        """Queue a UI test command. It is not an agent/store validation path."""
        self._validate_video_id(video_id)
        command_id = uuid.uuid4().hex
        try:
            self._commands.put(
                {
                    "command_id": command_id,
                    "operation": "open",
                    "video_id": video_id,
                },
                timeout=1,
            )
        except queue.Full as exc:
            raise PlayerBridgeError("Player command queue is full") from exc
        return command_id

    def _record_event(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._status.update(
                {
                    "connected": True,
                    "updated_at": time.time(),
                }
            )
            for key in ("player_state", "video_id", "current_time", "title", "message"):
                if key in payload:
                    self._status[key] = payload[key]
            command_id = payload.get("command_id")
            if payload.get("type") == "command_result" and isinstance(command_id, str):
                pending = self._pending.get(command_id)
                if pending is not None:
                    pending["result"] = dict(payload)
                    pending["event"].set()

    def _make_handler(self):
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "DoomscrollerLocalPlayer/1.0"

            def log_message(self, fmt: str, *args: Any) -> None:
                logger.debug("Player HTTP: " + fmt, *args)

            def _send_json(self, status: int, body: dict[str, Any]) -> None:
                data = json.dumps(body, separators=(",", ":")).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def _read_json(self) -> dict[str, Any]:
                raw_length = self.headers.get("Content-Length", "0")
                try:
                    length = int(raw_length)
                except ValueError as exc:
                    raise ValueError("Invalid Content-Length") from exc
                if length < 0 or length > _MAX_BODY_BYTES:
                    raise ValueError("Request body too large")
                raw = self.rfile.read(length)
                parsed = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(parsed, dict):
                    raise ValueError("JSON body must be an object")
                return parsed

            def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
                if self.path == "/" or self.path.startswith("/?"):
                    try:
                        data = bridge.player_html_path.read_bytes()
                    except OSError:
                        self._send_json(500, {"error": "Player UI could not be read"})
                        return
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
                    self.end_headers()
                    self.wfile.write(data)
                    return
                if self.path == "/api/status":
                    self._send_json(200, bridge.status())
                    return
                if self.path == "/api/next-command":
                    try:
                        command = bridge._commands.get(timeout=8)
                    except queue.Empty:
                        command = None
                    self._send_json(200, {"command": command})
                    return
                self._send_json(404, {"error": "Not found"})

            def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
                try:
                    payload = self._read_json()
                    if self.path == "/api/events":
                        bridge._record_event(payload)
                        self._send_json(202, {"accepted": True})
                        return
                    if self.path == "/api/manual-open":
                        video_id = payload.get("video_id")
                        bridge._validate_video_id(video_id)
                        command_id = bridge._queue_manual_open(video_id)
                        self._send_json(202, {"queued": True, "command_id": command_id})
                        return
                    self._send_json(404, {"error": "Not found"})
                except (ValueError, json.JSONDecodeError) as exc:
                    self._send_json(400, {"error": str(exc)})
                except PlayerBridgeError as exc:
                    self._send_json(503, {"error": str(exc)})

        return Handler


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    bridge = LocalPlayerBridge()
    url = bridge.start()
    print(f"Doomscroller player: {url}")
    print("This server is local-only. Press Ctrl+C to stop it.")
    webbrowser.open(url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping local player...")
        bridge.stop()


if __name__ == "__main__":
    main()
