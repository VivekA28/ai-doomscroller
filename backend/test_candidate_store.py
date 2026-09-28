from src.youtube_client import YouTubeClient
from src.candidate_builder import build_candidate
from src.candidate_store import CandidateStore


def main():
    youtube = YouTubeClient()

    results = youtube.search_videos(
        "JDM",
        max_results=5,
    )

    video_ids = [
        item["id"]["videoId"]
        for item in results.get("items", [])
    ]

    details = youtube.get_videos(video_ids)

    candidates = [
        build_candidate(video)
        for video in details.get("items", [])
    ]

    # Deliberately add the same candidates twice.
    store = CandidateStore()

    first_added = store.add_many(candidates)
    second_added = store.add_many(candidates)

    print(f"Candidates fetched: {len(candidates)}")
    print(f"First add:          {first_added}")
    print(f"Second add:         {second_added}")
    print(f"Store size:         {len(store)}")

    print("\nStored video IDs:")
    for candidate in store.all():
        print(candidate.video_id)


if __name__ == "__main__":
    main()
