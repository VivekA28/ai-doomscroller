from src.candidate_pipeline import CandidatePipeline
from src.youtube_client import YouTubeClient


def main():
    youtube = YouTubeClient()
    pipeline = CandidatePipeline(youtube)

    first = pipeline.search(
        "JDM",
        max_results=5,
    )

    print(f"First search - new candidates:  {len(first)}")
    print(f"Stored after first:             {len(pipeline.all_candidates())}")

    second = pipeline.search(
        "JDM cars",
        max_results=5,
    )

    print(f"Second search - new candidates: {len(second)}")
    print(f"Stored after second:            {len(pipeline.all_candidates())}")

    print("\nNew candidates from second search:")

    for candidate in second:
        print(
            f"{candidate.video_id} | "
            f"{candidate.duration_seconds}s | "
            f"{candidate.title}"
        )


if __name__ == "__main__":
    main()