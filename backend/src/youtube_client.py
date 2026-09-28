import os
from typing import Any
from src.quota import QuotaTracker

import requests
from dotenv import load_dotenv


load_dotenv()


class YouTubeAPIError(Exception):
    """Raised when the YouTube API returns an error."""


class YouTubeClient:
    BASE_URL = "https://www.googleapis.com/youtube/v3"

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

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        params = {
            **params,
            "key": self.api_key,
        }

        response = self.session.get(
            f"{self.BASE_URL}/{endpoint}",
            params=params,
            timeout=15,
        )

        if not response.ok:
            try:
                error = response.json()
            except ValueError:
                error = response.text

            raise YouTubeAPIError(
                f"YouTube API error ({response.status_code}): {error}"
            )

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
