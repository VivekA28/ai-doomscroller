"""Run the LLM-planned agent with an actual visible YouTube player.

Run from the backend directory:
    python run_live_agent.py --max-steps 8

Requires YOUTUBE_API_KEY and OPENAI_API_KEY in backend/.env.
"""
from __future__ import annotations

import argparse
import os
import time
import webbrowser

from dotenv import load_dotenv

# Load this backend's .env even when the script is launched from the repository root.
from pathlib import Path
load_dotenv(Path(__file__).resolve().parent / ".env")

from src.agent import Agent
from src.agent_action import ActionType, AgentAction
from src.candidate_pipeline import CandidatePipeline
from src.executor import ActionExecutor
from src.local_player_bridge import LocalPlayerBridge
from src.planner import Planner
from src.live_youtube_adapter import LiveYouTubeAdapter
from src.youtube_adapter import YouTubeAdapter
from src.youtube_client import YouTubeClient


def print_event(event: dict) -> None:
    """Print only the structured status emitted by the deterministic executor."""
    outcome = "OK" if event.get("success") else "FAILED"
    value = f" ({event['value']})" if event.get("value") else ""
    print(
        f"[agent {outcome}] {event.get('action', '?')}{value}"
        f" -> {event.get('state', '?')}: {event.get('message', '')}",
        flush=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the live Doomscroller agent")
    parser.add_argument(
        "--max-steps", type=int, default=8,
        help="maximum number of high-level actions (default: 8)",
    )
    parser.add_argument(
        "--port", type=int, default=8765,
        help="local player port (default: 8765)",
    )
    args = parser.parse_args()
    if not 1 <= args.max_steps <= 50:
        parser.error("--max-steps must be between 1 and 50")
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    return args


def main() -> int:
    args = parse_args()
    missing = [name for name in ("YOUTUBE_API_KEY", "OPENAI_API_KEY") if not os.getenv(name)]
    if missing:
        print(
            "Missing environment variable(s): " + ", ".join(missing)
            + ". Add them to backend/.env before running the live agent."
        )
        return 2

    topic = input("What topic should Doomscroller explore? ").strip()
    if not topic:
        print("No topic entered; exiting without starting the player.")
        return 2

    bridge = LocalPlayerBridge(port=args.port)
    try:
        player_url = bridge.start()
        print(f"Visible player: {player_url}")
        print("Opening the player in your browser…")
        webbrowser.open(player_url)

        discovery = YouTubeAdapter(CandidatePipeline(YouTubeClient()))
        adapter = LiveYouTubeAdapter(discovery, bridge)
        agent = Agent(adapter)
        executor = ActionExecutor(agent, event_sink=print_event)
        planner = Planner()

        print(f"Starting supervised agent run for: {topic!r}")
        print("The agent may cue videos; playback may require the browser's Play control.")
        agent.run(
            planner,
            AgentAction(ActionType.SEARCH, topic),
            max_steps=args.max_steps,
            executor=executor,
        )
        print(f"Agent run ended in state: {agent.get_state().value}")
        if agent.get_observation() is not None:
            observation = agent.get_observation()
            print(f"Current player item: {observation.current_item_id}")
            print(f"Candidates in current observation: {len(observation.candidates)}")
        print("The player server remains open. Press Ctrl+C to stop the session.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Doomscroller…")
    finally:
        bridge.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
