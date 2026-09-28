from src.candidate_pipeline import CandidatePipeline
from src.youtube_adapter import YouTubeAdapter, UnsupportedOperationError
from src.youtube_client import YouTubeClient


pipeline = CandidatePipeline(YouTubeClient())
adapter = YouTubeAdapter(pipeline)

adapter.search("JDM")

print("Search worked")
print("Candidates:", len(pipeline.all_candidates()))

adapter.wait()
print("Wait worked")

try:
    adapter.scroll()
except UnsupportedOperationError as e:
    print("Scroll correctly rejected:", e)