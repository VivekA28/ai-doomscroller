from src.youtube_client import YouTubeClient
from src.candidate_builder import build_candidate


def main():
    youtube = YouTubeClient()

    results = youtube.search_videos(
        "JDM",
        max_results=10,
    )

    video_ids = [
        item["id"]["videoId"]
        for item in results.get("items", [])
    ]

    if not video_ids:
        print("No videos found.")
        return

    details = youtube.get_videos(video_ids)

    print(f"Testing {len(details.get('items', []))} candidates:\n")

    for video in details.get("items", []):
        candidate = build_candidate(video)

        print(f"Title:          {candidate.title}")
        print(f"Channel:        {candidate.channel}")
        print(f"Video ID:       {candidate.video_id}")
        print(f"Duration:       {candidate.duration_seconds}s")
        print(f"Duration score: {candidate.signals.duration_score}")
        print(f"Text score:     {candidate.signals.text_score}")
        print(f"Visual score:   {candidate.signals.visual_score}")
        print("-" * 70)


if __name__ == "__main__":
    main()
