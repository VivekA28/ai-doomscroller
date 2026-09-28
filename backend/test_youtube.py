from src.youtube_client import YouTubeClient


def main():
    youtube = YouTubeClient()

    results = youtube.search_videos(
        "JDM",
        max_results=5,
    )

    print(f"Found {len(results.get('items', []))} results\n")

    video_ids = []

    for item in results.get("items", []):
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        channel = item["snippet"]["channelTitle"]

        video_ids.append(video_id)

        print(f"Title:   {title}")
        print(f"Channel: {channel}")
        print(f"URL:     https://www.youtube.com/watch?v={video_id}")
        print()

    if video_ids:
        details = youtube.get_videos(video_ids)

        print("Detailed metadata:")
        for video in details.get("items", []):
            print(
                video["id"],
                "→",
                video["contentDetails"]["duration"],
            )


if __name__ == "__main__":
    main()
