from src.agent_action import ActionType, AgentAction
from src.observation import Observation


class Planner:
    """
    Converts an observation into the next high-level agent action.

    This deterministic implementation is temporary.
    A future LLM-backed planner will implement the same interface.
    """

    def decide(self, observation: Observation) -> AgentAction:
        """Choose the next action from the current observation."""
        if observation.state != "observe":
            return AgentAction(type=ActionType.STOP)

        # For the deterministic smoke test, open one candidate and then stop.
        # A future planner can use the preserved candidate list/current item
        # plus richer metadata to continue exploration.
        if observation.current_item_id is not None:
            return AgentAction(type=ActionType.STOP)

        if observation.candidates:
            return AgentAction(
                type=ActionType.OPEN,
                value=observation.candidates[0],
            )

        return AgentAction(type=ActionType.STOP)
