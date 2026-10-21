---
description: "Task list for Podcast Ops-Hub Validation Slice"
---

# Tasks: Podcast Ops-Hub Validation Slice

**Input**: Design documents from `specs/001-podcast-ops-slice/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: INCLUDED — the constitution (Principle VI) requires automated tests for the
entity-resolution matcher and the decision rule, and the writeback exercised in mock mode.
These are governance-mandated, not optional.

**Organization**: Grouped by user story (US1 fuse → US2 decide → US3 act) so each stage of the
data → logic → action spine is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 / US2 / US3 (setup, foundational, and polish tasks carry no story label)
- Exact file paths are included in every task.

## Path Conventions

Single Python project: `src/podcast_ops/`, `tests/` at repository root (per plan.md).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure.

- [X] T001 Create project structure: `src/podcast_ops/{ingest,resolve,objects,logic,action,commands}/` (each with `__init__.py`) and `tests/{unit,integration,contract}/` per plan.md
- [X] T002 Initialize Python project: `pyproject.toml` (Python 3.11+) with deps `google-api-python-client`, `google-auth-oauthlib`, `spotipy`, `httpx`, `pydantic>=2`, `rapidfuzz`, `pytest`; add console entry `podcast-ops = podcast_ops.cli:main`
- [X] T003 [P] Configure tooling: `ruff` (lint) + `black` (format) + `pytest` config in `pyproject.toml`
- [X] T004 [P] Create `.gitignore` and `.env.example` (keys: `YOUTUBE_API_KEY`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `YOUTUBE_OAUTH_CLIENT_SECRETS`, `TEST_CHANNEL_ID`, `TEST_VIDEO_ID`, `TARGET_YOUTUBE_SOURCE`, `TARGET_SPOTIFY_SHOW`) — secrets MUST stay untracked (Principle VI)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config, object models, repositories, logging, and the **M0 access gate** that all
user stories depend on.

**⚠️ CRITICAL**: No user story work begins until this phase is complete. Per Principle V, the
M0 access gate (T011) MUST pass before any modeling/coding of ingestion proceeds.

- [X] T005 Implement env-based config loader (reads keys from environment/`.env`; never hardcodes secrets) in `src/podcast_ops/config.py`
- [X] T006 [P] Implement `RawPlatformRecord` model in `src/podcast_ops/ingest/records.py` — fields per data-model.md: `platform` enum(`youtube`,`spotify`), `platform_id` str, `title` str, `description` str|null, `published_at` date, `duration_seconds` int|null, `engagement` object|null, `raw` object, `fetched_at` datetime; immutable once built
- [X] T007 [P] Implement `Episode` + embedded `PlatformRef` models in `src/podcast_ops/objects/episode.py` — validation (quoted from data-model.md): "At least one of `youtube`/`spotify` MUST be set"; "`present_on` + `missing_from` MUST together equal {youtube, spotify} with no overlap"; "A two-sided `Episode` MUST carry exactly one YouTube ref and one Spotify ref (no fan-out)"
- [X] T008 [P] Implement audit/structured logging helper (append `WritebackAttempt`-style records to `run/action/audit.log`) and shared error types in `src/podcast_ops/action/audit_log.py`
- [X] T009 Implement `StagingRepository` (persist/load raw records under `run/staging/{platform}/*.json`, kept separate from objects) in `src/podcast_ops/ingest/staging.py` (depends on T006)
- [X] T010 Implement `EpisodeRepository` (persist/load fused objects at `run/objects/episodes.json`) in `src/podcast_ops/objects/repository.py` (depends on T007)
- [X] T011 **M0 ACCESS GATE** — implement `check-access` probes (YouTube Data API key read; Spotify Client-Credentials token + show read; test-channel OAuth token carrying `youtube.force-ssl`) in `src/podcast_ops/access_check.py`, and a thin argparse dispatcher wiring the `check-access` subcommand in `src/podcast_ops/cli.py`; running it MUST report OK for all three before modeling proceeds (Principle V; checklist in research.md)

**Checkpoint**: Config, models, repositories, logging ready and M0 access confirmed — user stories can begin.

---

## Phase 3: User Story 1 - Fuse episodes across two platforms (Priority: P1) 🎯 MVP

**Goal**: Read public metadata from YouTube + Spotify into staging, then resolve/conform into
fused `Episode` objects — the entity-resolution proof.

**Independent Test**: Run `ingest` then `fuse` against the chosen show; inspect
`run/objects/episodes.json` — every real-world episode on both platforms maps to exactly one
`Episode` (both refs), one-sided episodes record `missing_from`, with zero false merges and zero
missed matches (SC-002).

### Tests for User Story 1 ⚠️ (write first, ensure they FAIL)

- [X] T012 [P] [US1] Contract test for YouTube read mapping against a recorded fixture (engagement counts are integers) in `tests/contract/test_youtube_read.py` (per contracts/youtube-read.md)
- [X] T013 [P] [US1] Contract test for Spotify read mapping against a recorded fixture (`engagement` is `null`) in `tests/contract/test_spotify_read.py` (per contracts/spotify-read.md)
- [X] T014 [P] [US1] Unit tests for the matcher in `tests/unit/test_matcher.py`: similar-but-distinct titles NOT merged; same episode with mismatched titles IS matched; one-sided episode produces single object with correct `missing_from`; no fan-out on near-duplicate re-uploads

### Implementation for User Story 1

- [X] T015 [P] [US1] Implement `YouTubeGateway.list_episodes()` (Adapter over YouTube Data API v3: `playlistItems`/`search` + `videos.list` `snippet,contentDetails,statistics`; reads only; paginate; surface quota errors) in `src/podcast_ops/ingest/youtube_gateway.py` (per contracts/youtube-read.md)
- [X] T016 [P] [US1] Implement `SpotifyGateway.list_episodes()` (Adapter over Spotify Web API Client-Credentials: `GET /shows/{id}` + `/shows/{id}/episodes`; `duration_ms`→seconds; `engagement=null`; paginate; surface 429) in `src/podcast_ops/ingest/spotify_gateway.py` (per contracts/spotify-read.md)
- [X] T017 [US1] Implement `ingest` command: fetch from both gateways → write `RawPlatformRecord`s via `StagingRepository` in `src/podcast_ops/commands/ingest.py`, and register it in `src/podcast_ops/cli.py` (depends on T015, T016, T009)
- [X] T018 [US1] Implement the `Matcher` Strategy in `src/podcast_ops/resolve/matcher.py`: normalize titles (strip sponsor/prefix tags, episode-number tokens, punctuation) → block by release-date proximity → weighted score (title similarity via `rapidfuzz` + date closeness + duration closeness) → one-to-one match above threshold (no false merge, no missed match)
- [X] T019 [US1] Implement conform step building `Episode` objects from matched pairs and one-sided records (set `present_on`/`missing_from`/`match_confidence`) in `src/podcast_ops/resolve/conform.py` (depends on T018, T007)
- [X] T020 [US1] Implement `fuse` command: load staging → matcher → conform → persist via `EpisodeRepository` in `src/podcast_ops/commands/fuse.py`, register in `src/podcast_ops/cli.py` (depends on T019, T010)

**Checkpoint**: US1 fully functional — fused `Episode` objects exist and are inspectable.

---

## Phase 4: User Story 2 - Produce one decision (Priority: P2)

**Goal**: Run one read-only rule over `Episode` objects producing a decision; it changes nothing.

**Independent Test**: Run `decide` over known objects; it flags exactly the episodes that are on
Spotify but missing from YouTube and no others, leaving all objects and external state unchanged
(SC-003).

### Tests for User Story 2 ⚠️ (write first, ensure they FAIL)

- [X] T021 [P] [US2] Unit tests for the decision rule in `tests/unit/test_decision.py`: selects only episodes where `"spotify" in present_on AND "youtube" in missing_from`; "done" episodes not selected; rule mutates no `Episode` (read-only)

### Implementation for User Story 2

- [X] T022 [US2] Implement `Decision` model and the pure rule `spotify_without_youtube` (fields per data-model.md: `episode_id`, `action_needed` bool, `reason`, `rule`; MUST NOT mutate any `Episode` or external state) in `src/podcast_ops/logic/decision.py`
- [X] T023 [US2] Implement `decide` command: load episodes → apply rule → print/emit decisions in `src/podcast_ops/commands/decide.py`, register in `src/podcast_ops/cli.py` (depends on T022, T010)

**Checkpoint**: US1 + US2 both work independently; decisions derived cleanly, nothing mutated.

---

## Phase 5: User Story 3 - Execute one safe, logged writeback (Priority: P3)

**Goal**: For a selected episode, perform exactly one writeback to our own test channel — mock
first, then real — safe (retryable) and logged.

**Independent Test**: Run `act` (mock) → logs "would publish X to Y", zero external calls; run
`act --real` → one `videos.update` on the test video; rerun → `skipped_idempotent` (no
duplicate); every attempt in `run/action/audit.log` (SC-004, SC-005).

### Tests for User Story 3 ⚠️ (write first, ensure they FAIL)

- [X] T024 [P] [US3] Integration test for the mock-mode spine in `tests/integration/test_spine_mock.py`: full run in mock makes zero external calls; produces a `WritebackAttempt` with `mode=mock`; a second run returns `skipped_idempotent`

### Implementation for User Story 3

- [X] T025 [US3] Implement `WritebackAttempt` model and the `WritebackPort` interface (`publish(decision, episode) -> WritebackAttempt`) in `src/podcast_ops/action/writeback.py` (fields per data-model.md; `target` MUST be the owned test channel)
- [X] T026 [US3] Implement `MockWriteback` (logs `"would publish X to Y"`, no external call, `mode=mock`) in `src/podcast_ops/action/writeback.py` (depends on T025)
- [X] T027 [US3] Implement `YouTubeWriteback` (OAuth `videos.update` appending Spotify show-notes marker; **test-channel-only guard** — refuse any non-test target; **idempotency marker check** → `skipped_idempotent` on retry) in `src/podcast_ops/action/writeback.py` (depends on T025; per contracts/youtube-writeback.md)
- [X] T028 [US3] Implement `act` command (`--mock` default / `--real`) wiring decision → writeback port → audit log for every attempt in `src/podcast_ops/commands/act.py`, register in `src/podcast_ops/cli.py` (depends on T026, T027, T008, T023)

**Checkpoint**: Full data → logic → action spine runs end-to-end in mock, then real against the test channel.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end orchestration, docs, and the quality bar.

- [X] T029 [US3] Implement `run` command orchestrating the full spine (ingest → fuse → decide → act) with `--mock`/`--real` in `src/podcast_ops/commands/run.py`, register in `src/podcast_ops/cli.py` (depends on T020, T023, T028)
- [X] T030 [P] Write `README.md` with setup + the quickstart command sequence (M0→M3)
- [ ] T031 Run `quickstart.md` validation end-to-end (mock, then real against the test channel), confirm Definition of Done (SC-001..SC-006), and update `progress.md` milestone statuses
  - **Status**: MOCK portion DONE and validated (ingest-seed → fuse → decide → act mock; 16/16 tests pass). REAL-mode portion BLOCKED pending operator inputs: API credentials, the chosen show's IDs, and the throwaway test channel/video (see `.env.example`).

> **Live-pending note**: T011 (M0 access gate), the live transport in T017 (`ingest`), and the
> real writeback in T028/T029 are implemented in code and unit/integration-tested with injected
> fakes, but their *live* execution requires the operator-supplied credentials above. Per
> Principle V, run `podcast-ops check-access` (must report OK ×3) before any real-data run.
- [X] T032 [P] Code-quality pass: `ruff`/`black`/type-check clean, confirm no secrets committed, verify stage separation holds (logic read-only, only action writes) per Principle VI

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — start immediately.
- **Foundational (Phase 2)**: depends on Setup; **BLOCKS all user stories**; T011 (M0 gate) must pass before user-story coding.
- **User Stories (Phase 3→5)**: all depend on Foundational. US2 consumes US1 output; US3 consumes US2 output — so for this slice they run in **priority order P1 → P2 → P3** (the spine is sequential by nature).
- **Polish (Phase 6)**: depends on US1–US3 complete.

### Within Each User Story

- Tests written first and failing before implementation (constitution-mandated).
- Models → repositories → gateways/strategy → commands.
- `cli.py` registrations (T017, T020, T023, T028, T029) touch the same file → sequential, not parallel.

### Parallel Opportunities

- Setup: T003, T004 in parallel.
- Foundational: T006, T007, T008 in parallel (distinct files); T009/T010 after their models.
- US1: tests T012, T013, T014 in parallel; gateways T015, T016 in parallel.
- Writeback tasks T025→T026/T027 share `writeback.py` → sequential.
- Polish: T030, T032 in parallel.

---

## Parallel Example: User Story 1

```bash
# Tests first (parallel):
Task: "Contract test YouTube read in tests/contract/test_youtube_read.py"
Task: "Contract test Spotify read in tests/contract/test_spotify_read.py"
Task: "Matcher unit tests in tests/unit/test_matcher.py"

# Then gateways (parallel):
Task: "YouTubeGateway in src/podcast_ops/ingest/youtube_gateway.py"
Task: "SpotifyGateway in src/podcast_ops/ingest/spotify_gateway.py"
```

---

## Implementation Strategy

### MVP First (through User Story 1)

1. Phase 1 Setup → 2. Phase 2 Foundational (incl. **M0 gate T011**) → 3. Phase 3 US1 →
4. **STOP and VALIDATE**: inspect fused `Episode` objects for correct entity resolution.

US1 is the single most valuable proof (entity resolution). It is a legitimate stopping/demo point.

### Incremental Delivery

- Foundational + US1 → fused objects (entity-resolution proof).
- + US2 → a decision from the objects.
- + US3 (mock → real) → one safe, logged writeback = **Definition of Done** (SC-001). Stop there.

### Notes

- [P] = different files, no incomplete-task dependency.
- The spine is intentionally sequential (US2 needs US1's objects, US3 needs US2's decision), so
  parallelism lives mostly within a story, not across stories.
- Commit after each task or logical group; keep secrets out of commits (Principle VI).
- Hold the scope line: no extra platform, model, dashboard, loop, or generality (Principle I) —
  log any deviation in `decisions.md`.
