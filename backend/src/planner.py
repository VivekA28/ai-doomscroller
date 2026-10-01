import json
import os
from typing import Any, Protocol

import requests
from dotenv import load_dotenv

from src.agent_action import ActionType, AgentAction
from src.observation import Observation
from src.session_state import SessionState

load_dotenv()


class PlannerError(Exception):
    """Raised when the planner cannot produce a valid agent action."""


class LLMClient(Protocol):
    def complete(self, instructions: str, input_data: dict[str, Any]) -> str:
        ...


class OpenAIResponsesClient:
    BASE_URL = "https://api.openai.com/v1/responses"

    ACTION_SCHEMA = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [action.value for action in ActionType],
            },
            "value": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "null"},
                ],
            },
        },
        "required": ["action", "value"],
        "additionalProperties": False,
    }

    def __init__(self, api_key=None, model=None, timeout=30.0):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv(
            "DOOMSCROLLER_PLANNER_MODEL", "gpt-5.6-luna"
        )
        self.timeout = timeout
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set")

    def complete(self, instructions, input_data):
        payload = {
            "model": self.model,
            "instructions": instructions,
            "input": json.dumps(input_data, ensure_ascii=False),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "agent_action",
                    "strict": True,
                    "schema": self.ACTION_SCHEMA,
                }
            },
        }
        response = requests.post(
            self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )
        if not response.ok:
            try:
                error = response.json()
            except ValueError:
                error = response.text
            raise PlannerError(
                f"OpenAI API error ({response.status_code}): {error}"
            )
        data = response.json()
        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text" and isinstance(
                    content.get("text"), str
                ):
                    return content["text"]
        raise PlannerError("OpenAI response did not contain output text")


class Planner:
    SYSTEM_INSTRUCTIONS = """
You are the decision planner for an autonomous short-form content exploration agent.

Choose exactly one permitted high-level action from the supplied action set.
You do not control a browser, call APIs, or execute tools directly.
Your only job is to choose the next action from the current normalized observation.

Rules:
- SEARCH and EXPLORE require a non-empty topic/query in value.
- OPEN requires a candidate video ID in value.
- SCROLL, BACK, WAIT, and STOP must have value=null.
- Do not invent video IDs; OPEN only an unvisited ID present in the candidates list.
- Prefer continuing exploration when useful rather than stopping immediately.
- If there are no unvisited candidates, use SEARCH, EXPLORE, or STOP instead of reopening old content.
- STOP when there is no useful permitted next action or the session appears complete.
- Keep decisions based only on the supplied observation and session snapshot.
""".strip()

    def __init__(
        self,
        llm: LLMClient | None = None,
        session: SessionState | None = None,
    ):
        self._llm = llm
        self.session = session

    def set_session(self, session: SessionState) -> None:
        self.session = session

    @property
    def llm(self):
        if self._llm is None:
            self._llm = OpenAIResponsesClient()
        return self._llm

    def decide(self, observation: Observation) -> AgentAction:
        if observation.state != "observe":
            return AgentAction(type=ActionType.STOP)

        input_data = self._build_input(observation)
        raw = self.llm.complete(self.SYSTEM_INSTRUCTIONS, input_data)
        return self._parse_action(raw, observation)

    def _build_input(self, observation):
        candidates = list(observation.candidates)
        if self.session is not None:
            candidates = [
                candidate_id
                for candidate_id in candidates
                if not self.session.has_seen_item(candidate_id)
            ]

        return {
            "observation": {
                "state": observation.state,
                "topic": observation.topic,
                "current_item_id": observation.current_item_id,
                "candidates": candidates,
                "metadata": observation.metadata,
            },
            "available_actions": [action.value for action in ActionType],
            "session": (
                self.session.to_dict() if self.session is not None else None
            ),
        }

    def _parse_action(self, raw, observation):
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise PlannerError("Planner returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise PlannerError("Planner output must be a JSON object")
        try:
            action_type = ActionType(payload["action"])
        except (KeyError, ValueError, TypeError) as exc:
            raise PlannerError("Planner returned an invalid action") from exc
        value = payload.get("value")
        if value is not None and not isinstance(value, str):
            raise PlannerError("Planner action value must be a string or null")
        if action_type in {ActionType.SEARCH, ActionType.EXPLORE, ActionType.OPEN} and not value:
            raise PlannerError(f"{action_type.value.upper()} action requires a value")
        if action_type in {ActionType.SCROLL, ActionType.BACK, ActionType.WAIT, ActionType.STOP} and value is not None:
            raise PlannerError(f"{action_type.value.upper()} action must have value=null")

        if action_type == ActionType.OPEN:
            if value not in observation.candidates:
                raise PlannerError("OPEN target is not present in the candidate list")
            if self.session is not None and self.session.has_seen_item(value):
                raise PlannerError("OPEN target has already been viewed in this session")

        return AgentAction(type=action_type, value=value)
