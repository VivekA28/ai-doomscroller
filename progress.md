# AI Doomscroller --- Project Progress

## 0. Project Vision

Build a full-fledged AI agent that can autonomously doomscroll
short-form video content based on a user-provided keyword/topic.

Example:

> User: `JDM`

The agent should:

1.  Open a supported short-form content platform through an
    allowed/authorized interface.
2.  Search or navigate toward the requested topic.
3.  Observe the currently displayed short/video.
4.  Determine whether it is relevant to the user's goal.
5.  Scroll/navigate to the next item.
6.  Explore related topics when useful.
7.  Maintain session memory so it does not repeatedly explore the same
    things.
8.  Continue autonomously until paused/stopped.
9.  Show the entire process live so the user can watch the agent
    doomscrolling.
10. Provide controls such as Start, Pause, Resume, Stop, and Change
    Topic.

### Core principle

The agent should behave like a normal user navigating a permitted
interface, but **must not bypass authentication, CAPTCHAs, rate limits,
anti-bot protections, access controls, or platform restrictions**.

The project should use official APIs, permitted browser/UI automation,
or other authorized mechanisms wherever required.

------------------------------------------------------------------------

# 1. Product Concept

``` text
                    USER
                     |
              "doomscroll JDM"
                     |
                     v
              +--------------+
              |  AI AGENT    |
              +------+-------+
                     |
          +----------+----------+
          |          |          |
          v          v          v
      Navigator   Observer    Memory
          |          |          |
          +----------+----------+
                     |
                     v
              LIVE PLATFORM UI
                     |
                     v
                 Short Video
                     |
                     v
                  Observe
                     |
                     v
              Agent Decision
                /        \
          Scroll          Explore
             |               |
             +-------+-------+
                     |
                     v
                   LOOP
```

The key difference from a normal recommender is that the agent is not
merely producing a list of recommendations.

**The agent is actively navigating a content environment and deciding
what to do next.**

------------------------------------------------------------------------

# 2. Example User Experience

User enters:

``` text
Topic: JDM
```

Agent starts:

``` text
🤖 Starting doomscroll session

🔎 Searching: JDM
👀 Inspecting video
🏷️ Detected: Nissan R34, JDM, car edit
✅ Relevant
⬇️ Scrolling

👀 Inspecting video
🏷️ Detected: Ferrari, supercar
⚠️ Weak relevance
⬇️ Scrolling

👀 Inspecting video
🏷️ Detected: RB26, Skyline
✅ Highly relevant
🧠 Related topic discovered: RB26

🔎 Exploring: RB26
⬇️ Scrolling
...
```

The user sees the actual content/navigation while the side panel shows
high-level agent activity.

Do **not** expose hidden chain-of-thought. Show concise action/status
explanations instead.

------------------------------------------------------------------------

# 3. High-Level Architecture

``` text
                         +----------------+
                         |      USER      |
                         +-------+--------+
                                 |
                                 v
                       +-------------------+
                       |   Web/Desktop UI  |
                       +---------+---------+
                                 |
                     Start / Pause / Stop
                                 |
                                 v
                       +-------------------+
                       |   Agent Manager   |
                       +---------+---------+
                                 |
                +----------------+----------------+
                |                |                |
                v                v                v
        +-------------+   +-------------+   +-------------+
        |   Planner   |   |   Observer  |   |   Memory    |
        +------+------+   +------+------+   +------+------+
               |                 |                 |
               v                 v                 v
        +-------------+   +-------------+   +-------------+
        |  Navigator  |   | Multimodal  |   | Session DB |
        | / Tool Use  |   | Understander|   | / Vector DB|
        +------+------+   +------+------+   +-------------+
               |
               v
        +-------------------+
        | Platform Adapter  |
        +---------+---------+
                  |
          +-------+-------+
          |               |
          v               v
      YouTube/API    Instagram/API/
                     permitted UI
```

------------------------------------------------------------------------

# 4. Main Components

## 4.1 User Interface

Responsibilities:

-   Enter topic/keyword
-   Start session
-   Pause
-   Resume
-   Stop
-   Change topic
-   Show current video/page
-   Show agent status
-   Show discovered topics
-   Show session history
-   Show basic statistics

Initial UI can be a web application.

Possible stack:

-   Frontend: React/TypeScript
-   Backend: Python/FastAPI
-   Browser display: Playwright/browser integration where permitted

Do not commit to a framework until the platform feasibility stage is
complete.

------------------------------------------------------------------------

## 4.2 Agent Manager

The central controller.

Responsibilities:

-   Start/stop sessions
-   Maintain current state
-   Call the planner
-   Execute tools
-   Process observations
-   Maintain session context
-   Handle errors/timeouts
-   Enforce safety/platform constraints

Conceptual loop:

``` python
while session.running:

    observation = observe()

    decision = planner.decide(
        goal=session.goal,
        observation=observation,
        memory=session.memory
    )

    result = execute(decision)

    memory.update(observation, decision, result)
```

The actual implementation should use explicit state rather than an
uncontrolled infinite loop.

------------------------------------------------------------------------

# 5. Agent State Machine

Use a finite state machine instead of letting the LLM control
everything.

``` text
              +-------+
              | IDLE  |
              +---+---+
                  |
                START
                  |
                  v
             +---------+
             | SEARCH  |
             +----+----+
                  |
                  v
             +---------+
             | OBSERVE |
             +----+----+
                  |
            +-----+------+
            |            |
            v            v
        RELEVANT      IRRELEVANT
            |            |
            v            v
        EXPLORE       SCROLL
            |            |
            +-----+------+
                  |
                  v
             +---------+
             | OBSERVE |
             +---------+
                  |
             ... repeat
```

Additional states:

-   PAUSED
-   ERROR
-   AUTH_REQUIRED
-   RATE_LIMITED
-   STOPPED
-   SESSION_COMPLETE

------------------------------------------------------------------------

# 6. Planner / Decision Engine

The planner decides the next permitted action.

Possible actions:

``` text
SEARCH(topic)
SCROLL()
OPEN(item)
BACK()
EXPLORE(topic)
WAIT()
STOP()
```

Example:

``` json
{
  "action": "EXPLORE",
  "topic": "RB26",
  "reason": "Current content strongly relates to JDM and introduced RB26"
}
```

Keep action outputs structured and validated.

The LLM should **not** directly execute arbitrary browser commands.

------------------------------------------------------------------------

# 7. Observer

The observer converts the current UI/content into structured
information.

Potential inputs:

-   Visible text
-   Caption
-   Title
-   Creator/channel
-   Hashtags
-   Audio/song metadata where available
-   Video frames
-   Platform metadata
-   Current page state

Potential output:

``` json
{
  "topic_matches": ["JDM", "R34"],
  "entities": ["Nissan Skyline R34"],
  "content_type": "car_edit",
  "relevance": 0.94,
  "new_topics": ["RB26", "Tokyo drift"],
  "already_seen": false
}
```

Multimodal models can be used where visual understanding is required.

------------------------------------------------------------------------

# 8. Memory

Two levels:

## Session memory

Stores:

-   Videos/items encountered
-   Topics discovered
-   Searches performed
-   Actions taken
-   Relevance scores
-   Errors
-   Current exploration path

Example:

``` text
JDM
 ├── R34
 │    └── RB26
 ├── drifting
 └── Initial D
```

## Long-term memory

Optional later feature.

Could remember:

-   Frequently requested topics
-   User preferences
-   Topics the user repeatedly stops/starts
-   Preferred exploration depth

Do not build long-term personalization until the core agent works.

------------------------------------------------------------------------

# 9. Topic Exploration

This is one of the most important agent features.

Starting topic:

``` text
JDM
```

Agent discovers:

``` text
JDM
 |
 +-- R34
 |    +-- RB26
 |    +-- tuning
 |
 +-- drifting
 |    +-- Formula Drift
 |
 +-- Initial D
      +-- Eurobeat
```

The agent should balance:

``` text
70% direct relevance
20% related exploration
10% novelty
```

These percentages are initial hypotheses, not fixed requirements.

They should eventually be configurable and evaluated experimentally.

------------------------------------------------------------------------

# 10. Content Selection

The system should maintain a candidate/content representation.

Possible features:

``` text
text similarity
visual similarity
topic similarity
creator/channel
audio similarity
freshness
previously seen
session frequency
exploration value
```

Initially use simple rules + embeddings.

Later build an ML ranking model.

------------------------------------------------------------------------

# 11. Recommendation / Ranking Layer

Do not make the LLM responsible for every recommendation.

Long-term architecture:

``` text
Content
   |
   v
Feature extraction
   |
   v
Embedding + metadata
   |
   v
Candidate generation
   |
   v
Ranking model
   |
   v
Agent decision
```

The agent decides **what to explore/do**.

The ranking system helps determine **which available content is worth
prioritizing**.

------------------------------------------------------------------------

# 12. Platform Adapter Architecture

Do not hard-code Instagram/YouTube logic throughout the project.

Use adapters:

``` text
PlatformAdapter
|
+-- YouTubeAdapter
|
+-- InstagramAdapter
|
+-- FutureAdapter
```

Possible interface:

``` python
class PlatformAdapter:

    def search(self, query):
        pass

    def current_content(self):
        pass

    def next_content(self):
        pass

    def open_content(self, content_id):
        pass

    def get_metadata(self):
        pass
```

Actual methods will depend on what each platform officially permits.

------------------------------------------------------------------------

# 13. Platform Compliance Requirement

Before implementation of any real platform integration, document:

-   Official API availability
-   Authentication requirements
-   Permissions
-   Rate limits
-   Content access restrictions
-   Automation restrictions
-   Data storage/caching rules
-   Display/redistribution requirements
-   Terms applicable to the chosen integration

Never:

-   bypass CAPTCHAs
-   bypass rate limits
-   defeat anti-bot systems
-   evade authentication
-   steal session tokens/cookies
-   bypass access controls
-   build mechanisms specifically intended to evade platform detection

If a platform does not permit a required capability, redesign the
integration rather than circumventing it.

------------------------------------------------------------------------

# 14. Live Visualization

The user must be able to watch the agent operate.

Two possible architectures:

## Browser-view approach

``` text
Agent
  |
  v
Browser automation layer
  |
  v
Visible browser
  |
  +----> UI displays browser
```

## Remote browser stream

``` text
Agent Browser
      |
      v
Screen/frame stream
      |
      v
Frontend
      |
      v
User watches live
```

The second approach is preferable if we eventually deploy the system
remotely.

------------------------------------------------------------------------

# 15. Agent Activity Panel

Show high-level events:

``` text
23:41:03  🔎 Searching "JDM"
23:41:05  👀 Inspecting current video
23:41:07  ✅ Strong topic match
23:41:08  🧠 Discovered "RB26"
23:41:09  ⬇️ Scrolling
23:41:12  ❌ Low relevance
23:41:13  ⬇️ Scrolling
23:41:16  🔎 Exploring "RB26"
```

Do not display private chain-of-thought.

------------------------------------------------------------------------

# 16. Technology Roadmap

## Phase 0 --- Feasibility

-   [x] Research Instagram official API capabilities
-   [x] Research YouTube official API capabilities
-   [x] Determine permitted navigation/automation options
-   [x] Determine authentication requirements
-   [x] Determine content-display/caching requirements
-   [x] Select first supported platform
-   [x] Document limitations

## Phase 1 --- Foundations

-   [x] Python project structure
-   [x] Git repository
-   [x] Configuration management
-   [ ] Logging
-   [ ] Basic FastAPI backend
-   [ ] Basic frontend
-   [x] LLM API integration
-   [x] Structured agent actions
-   [x] Local API quota accounting

## Phase 2 --- Agent Core

-   [x] Agent state machine
-   [x] Planner
-   [ ] Tool interface
-   [x] Session state
-   [x] Action validation
-   [ ] Error handling
-   [ ] Pause/resume/stop

## Phase 3 --- Platform Integration

-   [x] Platform adapter interface
-   [x] Short-form candidate/filtering layer
-   [ ] First real platform adapter
-   [ ] Authorized authentication
-   [ ] Search/navigation
-   [ ] Content retrieval/display
-   [ ] Next-content navigation
-   [ ] Rate-limit handling

## Phase 4 --- Vision / Content Understanding

-   [ ] Caption/text extraction
-   [ ] Metadata extraction
-   [ ] Video frame sampling
-   [ ] Multimodal understanding
-   [ ] Topic classification
-   [ ] Relevance scoring
-   [ ] Duplicate detection

## Phase 5 --- Agentic Exploration

-   [ ] Related-topic discovery
-   [ ] Exploration tree
-   [ ] Topic memory
-   [ ] Novelty mechanism
-   [ ] Search strategy
-   [ ] Exploration depth
-   [ ] Stop conditions

## Phase 6 --- Recommendation Layer

-   [ ] Embeddings
-   [ ] Candidate retrieval
-   [ ] Ranking
-   [ ] User/session feedback
-   [ ] Behavioral signals
-   [ ] Ranking evaluation
-   [ ] Personalization

## Phase 7 --- Live UI

-   [ ] Live browser/content view
-   [ ] Agent activity panel
-   [ ] Current topic
-   [ ] Exploration graph
-   [ ] Pause/resume
-   [ ] Stop
-   [ ] Session statistics
-   [ ] Error/status notifications

## Phase 8 --- Memory

-   [ ] Session database
-   [ ] Content history
-   [ ] Topic history
-   [ ] Vector store
-   [ ] Optional long-term preferences

## Phase 9 --- Evaluation

Measure:

-   Topic relevance
-   Novelty
-   Duplicate rate
-   Exploration quality
-   Session length
-   User satisfaction
-   Latency
-   API usage
-   Cost per session
-   Failure rate

Create test sessions for:

``` text
JDM
anime
football
music
fashion
memes
technology
```

## Phase 10 --- Production

-   [ ] Authentication
-   [ ] Secure credential handling
-   [ ] Deployment
-   [ ] Observability
-   [ ] Rate limiting
-   [ ] Cost controls
-   [ ] Platform compliance review
-   [ ] Failure recovery
-   [ ] Privacy review
-   [ ] Documentation

------------------------------------------------------------------------

# 17. Suggested Repository Structure

``` text
ai-doomscroller/
│
├── README.md
├── progress.md
├── .env.example
├── requirements.txt
│
├── backend/
│   ├── main.py
│   │
│   ├── agent/
│   │   ├── manager.py
│   │   ├── planner.py
│   │   ├── state.py
│   │   └── actions.py
│   │
│   ├── platforms/
│   │   ├── base.py
│   │   ├── youtube.py
│   │   └── instagram.py
│   │
│   ├── vision/
│   │   ├── observer.py
│   │   └── analyzer.py
│   │
│   ├── memory/
│   │   ├── session.py
│   │   └── vector_store.py
│   │
│   ├── ranking/
│   │   ├── features.py
│   │   ├── candidates.py
│   │   └── ranker.py
│   │
│   └── tools/
│       ├── search.py
│       └── navigation.py
│
├── frontend/
│   └── ...
│
├── tests/
│   ├── agent/
│   ├── platforms/
│   └── ranking/
│
└── docs/
    ├── architecture.md
    ├── platform-research.md
    └── decisions.md
```

------------------------------------------------------------------------

# 18. Development Rules

1.  Build one component at a time.
2.  Test every component independently.
3.  Do not introduce an agent framework before understanding the
    underlying loop.
4.  Keep platform-specific code isolated.
5.  Never hard-code credentials.
6.  Log agent actions.
7.  Keep LLM outputs structured.
8.  Validate every tool/action before execution.
9.  Never allow arbitrary LLM-generated browser commands to execute
    directly.
10. Design for platform compliance from the beginning.
11. Prefer simple deterministic logic where an LLM is unnecessary.
12. Measure the system instead of assuming it works.

------------------------------------------------------------------------

# 19. Definition of Done

The project reaches the first major milestone when:

``` text
User enters a keyword
        ↓
Agent starts
        ↓
Real permitted content interface opens
        ↓
Agent navigates content
        ↓
User can see the agent operating live
        ↓
Agent observes content
        ↓
Agent determines relevance
        ↓
Agent scrolls/navigates
        ↓
Agent discovers related topics
        ↓
Agent remembers the session
        ↓
Agent continues autonomously
        ↓
User can pause/resume/stop
```

The final product should feel like:

> **"I gave an AI a topic and it went down the rabbit hole for me."**

------------------------------------------------------------------------

# 20. Immediate Next Task

Platform feasibility research established YouTube as the first integration target.
The deterministic candidate/data layer, agent state machine, session state,
and LLM planner integration are implemented and tested.

Next focus:

### Platform Adapter / Execution Boundary

Build the next deterministic layer between the planner and the real platform:

1. Keep all platform-specific operations behind `PlatformAdapter`.
2. Define the execution contract for `SEARCH`, `OPEN`, `SCROLL`, `BACK`, `WAIT`,
   `EXPLORE`, and `STOP`.
3. Connect the existing YouTube candidate/content layer to the adapter cleanly.
4. Add deterministic handling for unsupported operations instead of allowing
   the planner to issue arbitrary platform commands.
5. Add error, rate-limit, and authentication-required handling at the adapter
   boundary.
6. Test the adapter independently before introducing live UI/browser control.

The goal of this step is to make the planner capable of producing validated
high-level actions while the adapter remains the only layer allowed to perform
platform operations.

------------------------------------------------------------------------

# Current Status

**Project:** AI Doomscroller

**Status:** Foundations complete / first platform integration in progress

**Current goal:** Build a real autonomous short-form-content
doomscrolling agent with a live view of its actions.

**Latest checkpoint:** 35/35 offline tests passing after hardening Agent/Planner session integration and graceful PlannerError handling.

## Completed so far

### Project setup

- Git repository initialized.
- Python environment created with Python 3.12.6.
- `.env` configuration added for local secrets.
- `python-dotenv` and `requests` installed.
- API credentials are kept out of source control.

### Platform feasibility

- **YouTube selected as the first platform integration.**
- YouTube Data API v3 is usable for the initial content-discovery layer.
- `search.list` can search public video content by keyword.
- `videos.list` can retrieve detailed metadata including duration.
- There is no direct API field that simply identifies every result as a
  YouTube Short, so short-form detection will be implemented as a
  candidate/filtering layer rather than assuming `videoDuration=short`
  means Shorts.
- API quota must be treated as a design constraint; search requests are
  substantially more expensive than metadata requests, so unnecessary
  repeated searches should be avoided.
- Instagram remains a future adapter. Its official interfaces do not
  provide the unrestricted ordinary personalized Reels feed/navigation
  needed for the full original concept, so we will not build an
  unauthorized scraper or bypass platform restrictions.

### YouTube client

Implemented:

``` text
backend/
├── .env
├── .venv/
├── requirements.txt
├── src/
│   ├── __init__.py
│   └── youtube_client.py
└── test_youtube.py
```

`YouTubeClient` currently supports:

- Keyword video search.
- Pagination through YouTube `pageToken`.
- Batch metadata lookup for video IDs.
- API error handling.

### API integration test

The end-to-end YouTube API test is working with the query `JDM`.
The test successfully returned 5 videos and then fetched their detailed
metadata. Observed durations included:

``` text
PT15S
PT17S
PT1M
PT2M55S
PT18S
```

This confirms that the local environment, API key loading, YouTube search,
and metadata retrieval are functioning end-to-end.

## Immediate next task

The **Shorts candidate/filtering layer, quota layer, deterministic agent-control foundation, session state, and LLM planner integration are implemented and tested**.

Next work should continue from the **platform adapter / execution boundary**. The current YouTube adapter exposes the platform interface and candidate/content operations, but full scrolling/navigation execution is not implemented yet.


### Latest Agent/Planner hardening checkpoint

Implemented and tested:

- `STOP` can be executed from `IDLE` without an existing `SessionState`.
- Session action recording is guarded when no session exists.
- Successful `OPEN` operations record the item as seen even when the platform adapter returns no metadata (`None`).
- `Agent.run()` handles `PlannerError` explicitly, transitions to `ERROR`, and terminates the run cleanly instead of propagating the planner error unhandled.
- `test_planner.py` can be executed directly from the `backend` directory without a `src` import-path failure.
- Planner session integration has explicit tests for filtering seen candidates, including the session snapshot, and rejecting already-seen `OPEN` targets.

Validation:

``` text
python3 tests/test_planner.py
Ran 11 tests
OK

python3 -m unittest discover -s . -p 'test_*.py' -v
Ran 35 tests
OK
```

The full offline suite currently passes **35/35 tests**.

### Completed: Short-form candidate layer

Implemented:

- `src/models.py`
  - `CandidateSignals`
  - `VideoCandidate`
- `src/short_detector.py`
  - Deterministic ISO-8601 YouTube duration parser
  - `duration_score`
  - `text_score`
  - `detect_signals`
- `src/candidate_builder.py`
  - Converts YouTube metadata into `VideoCandidate`
- `src/candidate_store.py`
  - Session-level canonical `video_id` deduplication
- `src/candidate_pipeline.py`
  - Search → metadata enrichment → candidate construction → deduplication
  - Returns only newly discovered candidates

### Detector design

Signals remain independent:

``` text
duration_score
text_score
visual_score = None
```

Duration is treated as evidence, not authoritative Shorts classification.
Visual evidence will be added later.

### Validation completed

- Duration parser tested successfully.
- Candidate builder tested against real YouTube results.
- Detector tested across 10 real YouTube results.
- Candidate store deduplication tested successfully.
- Cross-search pipeline test:
  - First search: 5 new candidates
  - Second search: 3 new candidates
  - Total unique candidates: 8

The candidate/filtering layer is now implemented and tested.

### Agent loop + session state

Implemented and tested:

- `src/agent.py` provides a bounded planner → action → observation loop.
- The end-to-end offline agent tests use scripted/mocked planners, so the suite does not require an OpenAI API key.
- `src/session_state.py` provides deterministic per-session memory for the goal, current topic, seen item IDs, searched topics, discovered topics, and action history.
- Session state has focused mutation/query methods and a JSON-safe `to_dict()` snapshot for planner/UI use.
- Search and discovered-topic deduplication are case-insensitive.
- The agent records executed actions and session items.
- The agent rejects reopening an item that has already been viewed in the current session.
- The planner receives a read-only session snapshot and filters already-seen candidates before presenting them to the LLM.
- The planner also rejects an `OPEN` action targeting an already-seen item as a second deterministic validation boundary.

Session state is now integrated with the agent and planner. The LLM can consume session context but does not directly mutate session memory.

### LLM Planner

Implemented:

- `src/planner.py` now provides the LLM-backed `Planner` using the OpenAI Responses API.
- The planner keeps the existing `Planner.decide(observation) -> AgentAction` contract.
- LLM output is constrained to the existing `ActionType` values and `{action, value}` schema.
- `OPEN` targets are validated against the current observation candidate list.
- Actions that require values (`SEARCH`, `EXPLORE`, `OPEN`) and actions that must not have values (`SCROLL`, `BACK`, `WAIT`, `STOP`) are validated before returning.
- Non-`observe` states stop without making an LLM call.
- The LLM client is dependency-injected, allowing completely offline planner tests.
- The default model can be configured with `DOOMSCROLLER_PLANNER_MODEL`; the current default is `gpt-5.6-luna`.
- The planner does not receive or execute arbitrary browser commands.

### Planner validation

- `test_planner.py` covers valid actions, malformed JSON, unknown actions, invalid targets, invalid values, controlled planner input, non-observe behavior, session snapshots, filtering of seen candidates, and rejection of reopening seen items.
- The planner remains dependency-injected for completely offline tests.

### Agent core foundation

Implemented and independently tested:

- `src/agent_state.py`
  - Explicit agent state enum covering search, observation, decision, navigation, errors, rate limiting, pause/stop, and session completion.
- `src/agent.py`
  - Deterministic state-transition validation.
  - `execute()` validates high-level actions before changing state.
  - Invalid transitions are rejected with `InvalidTransitionError`.
- `src/agent_action.py`
  - Structured `ActionType` enum and `AgentAction` dataclass.
  - Actions currently include search, scroll, open, back, explore, wait, and stop.
- `src/platform_adapter.py`
  - Abstract platform interface for search, scroll, open, back, and wait.

### Quota management

Implemented and tested:

- `src/quota.py`
  - Local YouTube quota budget tracker.
  - Tracks estimated costs for `search.list` and `videos.list`.
  - Exposes remaining budget and status.
  - Raises `QuotaExceededError` when the local budget would be exceeded.
- `YouTubeClient` now accounts for quota usage for search and metadata calls.
- `CandidatePipeline.quota_status()` exposes current quota state to the future agent.

This is a local safety/accounting layer, not Google's authoritative quota state.

### Current data flow

``` text
keyword
   ↓
YouTube search
   ↓
video_id deduplication
   ↓
metadata enrichment
   ↓
short-form candidate signals
   ↓
VideoCandidate
   ↓
new-candidate pipeline
   ↓
future ranking / agent decision
```

The bounded agent loop and planner integration now exist and are tested,
but the project is **not yet a real live doomscrolling agent**. The remaining
core work is to connect the deterministic control loop to an authorized platform
execution layer and eventually expose that activity through the live UI.


## Important design decision

Do not equate `duration < 60 seconds` with an authoritative YouTube
Shorts classification. It is an initial short-form candidate heuristic.
The later platform/content layer can add stronger signals where available.

**Do not:** Start with a fake feed, generic chatbot, uncontrolled scraper,
or LLM-controlled arbitrary browser commands. The LLM/decision layer now
exists behind structured action validation, but platform execution must still
remain behind the deterministic adapter/tool boundary.
