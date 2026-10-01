import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
from src.observation import Observation
from src.planner import Planner, PlannerError

load_dotenv()


def main():
    print("=" * 60)
    print("LIVE PLANNER SMOKE TEST")
    print("=" * 60)

    use_mock = "--mock" in sys.argv
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("DOOMSCROLLER_PLANNER_MODEL", "gpt-5.6-luna")

    print(f"Mode:               {'MOCK (offline verification)' if use_mock else 'LIVE API'}")
    print(f"API Key configured: {'Yes (set)' if api_key else 'NO (not set)'}")
    print(f"Target model:       {model if not use_mock else 'Mock-LLM'}")
    print("-" * 60)

    if not use_mock and not api_key:
        print("\n[!] OPENAI_API_KEY is not set.")
        print("To run the live test:")
        print("  1. Add OPENAI_API_KEY=your_key to backend/.env")
        print("  2. (Optional) Set DOOMSCROLLER_PLANNER_MODEL in backend/.env (e.g. gpt-4o-mini)")
        print("\nTo test the harness pipeline offline, run:")
        print("  python3 test_planner_live.py --mock")
        sys.exit(1)

    # 1. Observation
    observation = Observation(
        state="observe",
        topic="JDM",
        current_item_id=None,
        candidates=["dQw4w9WgXcQ", "abc123xyz89"],
        metadata={
            "candidate_count": 2,
            "item": {
                "video_id": "dQw4w9WgXcQ",
                "title": "Nissan Skyline R34 GT-R V-Spec II #shorts",
                "channel": "JDM Culture",
                "duration_seconds": 28,
                "signals": {
                    "duration_score": 1.0,
                    "text_score": 1.0,
                    "visual_score": None,
                },
            },
        },
    )

    print("1. Input Normalized Observation:")
    print(f"   State:       {observation.state}")
    print(f"   Topic:       {observation.topic}")
    print(f"   Candidates:  {observation.candidates}")
    print(f"   Metadata:    {observation.metadata.get('candidate_count')} candidates available")
    print("-" * 60)

    # 2. LLM Call via Planner
    if use_mock:
        from tests.test_planner import FakeLLM
        print("2. Dispatching observation to Mock LLM (simulating model output)...")
        planner = Planner(FakeLLM('{"action": "open", "value": "dQw4w9WgXcQ"}'))
    else:
        print("2. Dispatching observation to live LLM via Planner.decide()...")
        planner = Planner()

    try:
        # 3. AgentAction & 4. Validation inside decide()
        action = planner.decide(observation)

        # 5. Print Result
        print("-" * 60)
        print("SMOKE TEST SUCCESSFUL!")
        print("-" * 60)
        print(f"Action Type:  {action.type.value}")
        print(f"Action Value: {action.value}")
        print(f"AgentAction:  {action}")
        print("-" * 60)
        print("Validation:   PASSED (ActionType is valid and value satisfies constraints)")

    except PlannerError as e:
        print("-" * 60)
        print("PLANNER ERROR ENCOUNTERED:")
        print(e)
        sys.exit(1)
    except Exception as e:
        print("-" * 60)
        print("UNEXPECTED ERROR:")
        print(f"{type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
