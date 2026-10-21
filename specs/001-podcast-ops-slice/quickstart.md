# Quickstart: Podcast Ops-Hub Validation Slice

A run/validation guide proving the data → logic → action spine end-to-end. Implementation
details live in `tasks.md` and the code; this file is how you *run and verify* the slice.

## Prerequisites

- Python 3.11+
- A YouTube Data API v3 **API key** (public reads)
- Spotify app **client id + secret** (Client Credentials)
- A **throwaway YouTube test channel** you own, with OAuth client credentials and a token
  carrying scope `youtube.force-ssl` (for the real writeback)
- One chosen **real public show present on both YouTube and Spotify**, with its YouTube
  channel/uploads id and Spotify show id

Secrets go in a local untracked `.env` (never committed):

```
YOUTUBE_API_KEY=...
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
YOUTUBE_OAUTH_CLIENT_SECRETS=./secrets/oauth_client.json   # test channel, real mode only
TEST_CHANNEL_ID=...
TEST_VIDEO_ID=...            # owned test video whose show notes we update
TARGET_YOUTUBE_SOURCE=...    # chosen show's YouTube channel/uploads id
TARGET_SPOTIFY_SHOW=...      # chosen show's Spotify show id
```

## Setup

```
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e .
```

## M0 — Confirm API access (gate before modeling)

```
python -m podcast_ops.cli check-access
```
**Expected**: reports OK for (1) YouTube read, (2) Spotify read, (3) test-channel OAuth write
scope. If any fails, stop — do not proceed to modeling (Principle V). See the checklist in
[research.md](./research.md).

## M1 — Read + fuse (entity-resolution proof)

```
python -m podcast_ops.cli ingest     # raw → run/staging/{youtube,spotify}/
python -m podcast_ops.cli fuse        # staging → run/objects/episodes.json
```
**Expected**: each real-world episode present on both platforms becomes exactly one `Episode`
with both refs; one-sided episodes record `missing_from`. Inspect `episodes.json`; confirm no
false merges and no missed matches (SC-002).

## M2 — Decide (one read-only rule)

```
python -m podcast_ops.cli decide
```
**Expected**: prints episodes where `action_needed=true` ("on Spotify, no YouTube clip yet")
and nothing else; `episodes.json` and all external state unchanged (SC-003).

## M3 — Act (one safe, logged writeback)

```
python -m podcast_ops.cli act            # mock (default): logs "would publish X to Y"
python -m podcast_ops.cli act --real     # real: one videos.update on the test video
python -m podcast_ops.cli act --real     # run again → skipped_idempotent (no duplicate)
```
**Expected**: mock makes zero external calls (SC-004); real applies exactly one change to the
test channel; a repeat is `skipped_idempotent`; every attempt is in `run/action/audit.log`
(SC-005). A simulated failure can be retried to success.

## Full spine (Definition of Done)

```
python -m podcast_ops.cli run            # mock end-to-end
python -m podcast_ops.cli run --real     # real end-to-end against the test channel
```
**Done** when one `--real` run pulls the show from both platforms, fuses correctly, applies the
rule, and performs one safe, logged writeback to the test channel (SC-001). Stop there.

## Tests

```
pytest tests/unit          # matcher + decision rule
pytest tests/integration   # mock-mode spine
pytest tests/contract      # gateway response shapes (fixtures)
```
