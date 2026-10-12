import os
from typing import Any

import requests
from dotenv import load_dotenv

from src.quota import QuotaTracker

load_dotenv()


class YouTubeAPIError(Exception):
    """Raised when the YouTube Data API returns an unclassified error."""


class YouTubeAuthenticationError(YouTubeAPIError):
    """Raised when the API key or authorization is invalid."""


class YouTubeRateLimitError(YouTubeAPIError):
    """Raised when YouTube rejects a request due to quota/rate limits."""


class YouTubeClient:
    BASE_URL = "https://www.googleapis.com/youtube/v3"

    AUTH_ERROR_REASONS = {
        "keyinvalid",
        "invalidcredentials",
        "iprefererblocked",
        "accessnotconfigured",
        "insufficientpermissions",
    }
    RATE_LIMIT_REASONS = {
        "quotaexceeded",
        "dailylimitexceeded",
        "ratelimitexceeded",
        "userratelimitexceeded",
    }

    def __init__(
        self,
        api_key: str | None = None,
        quota_tracker: QuotaTracker | None = None,
    ):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY is not set")

        self.session = requests.Session()
        self.quota = quota_tracker or QuotaTracker()

    @classmethod
    def _raise_api_error(cls, status_code: int, payload: Any) -> None:
        """Raise a typed API exception from Google's structured error body."""
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        details = error.get("errors", []) if isinstance(error, dict) else []
        reasons = {
            str(item.get("reason", "")).casefold()
            for item in details
            if isinstance(item, dict)
        }
        message = f"YouTube API error ({status_code}): {payload}"

        if status_code == 401 or reasons.intersection(cls.AUTH_ERROR_REASONS):
            raise YouTubeAuthenticationError(message)
        if status_code == 429 or reasons.intersection(cls.RATE_LIMIT_REASONS):
            raise YouTubeRateLimitError(message)
        raise YouTubeAPIError(message)

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        request_params = {
            **params,
            "key": self.api_key,
        }

        response = self.session.get(
            f"{self.BASE_URL}/{endpoint}",
            params=request_params,
            timeout=15,
        )

        if not response.ok:
            try:
                error = response.json()
            except ValueError:
                error = response.text
            self._raise_api_error(response.status_code, error)

        return response.json()

    def search_videos(
        self,
        query: str,
        *,
        max_results: int = 10,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """Search for public YouTube videos matching a query."""
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
        }

        if page_token:
            params["pageToken"] = page_token

        self.quota.spend("search.list")
        return self._get("search", params)

    def get_videos(self, video_ids: list[str]) -> dict[str, Any]:
        """Fetch detailed metadata for a batch of video IDs."""
        if not video_ids:
            return {"items": []}

        self.quota.spend("videos.list")
        return self._get(
            "videos",
            {
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(video_ids),
            },
        )
