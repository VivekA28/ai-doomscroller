from src.candidate_builder import build_candidate
from src.candidate_store import CandidateStore
from src.youtube_client import YouTubeClient


class CandidatePipeline:
    def __init__(self, youtube: YouTubeClient):
        self.youtube = youtube
        self.store = CandidateStore()

    def search(self, query: str, max_results: int = 10) -> list:
        """
        Search YouTube and return only newly discovered candidates.
        """
        results = self.youtube.search_videos(
            query,
            max_results=max_results,
        )

        video_ids = [item["id"]["videoId"] for item in results.get("items", [])]

        if not video_ids:
            return []

        details = self.youtube.get_videos(video_ids)

        new_candidates = []

        for video in details.get("items", []):
            candidate = build_candidate(video)

            if self.store.add(candidate):
                new_candidates.append(candidate)

        return new_candidates

    def all_candidates(self) -> list:
        """Return all unique candidates seen by this pipeline."""
        return self.store.all()

    def quota_status(self) -> dict:
        """Return the current YouTube API quota status."""
        return self.youtube.quota.status()
