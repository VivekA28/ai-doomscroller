class QuotaExceededError(Exception):
    """Raised when the local API quota budget is exhausted."""


class QuotaTracker:
    """
    Tracks estimated YouTube Data API quota usage for the session.

    This is a local safety budget, not Google's authoritative quota state.
    """

    DEFAULT_DAILY_BUDGET = 10_000

    COSTS = {
        "search.list": 100,
        "videos.list": 1,
    }

    def __init__(self, budget: int = DEFAULT_DAILY_BUDGET):
        self.budget = budget
        self.used = 0

    @property
    def remaining(self) -> int:
        return max(0, self.budget - self.used)

    def can_spend(self, operation: str, units: int = 1) -> bool:
        cost = self.COSTS.get(operation, 0) * units
        return self.used + cost <= self.budget

    def spend(self, operation: str, units: int = 1) -> None:
        cost = self.COSTS.get(operation, 0) * units

        if self.used + cost > self.budget:
            raise QuotaExceededError(
                f"Quota budget exceeded: "
                f"used={self.used}, requested={cost}, budget={self.budget}"
            )

        self.used += cost

    def status(self) -> dict:
        return {
            "budget": self.budget,
            "used": self.used,
            "remaining": self.remaining,
        }
