# Podcast Ops-Hub — Validation Slice

A deliberately narrow vertical slice that proves one end-to-end spine of the
**data → logic → action** pattern:

1. **Data** — read public metadata for one real show from **YouTube + Spotify** into a
   staging area, then resolve + conform it into fused `Episode` objects (entity resolution).
2. **Logic** — one read-only rule decides ("on Spotify, no YouTube clip yet").
3. **Action** — one safe, logged, **mock-first** writeback to our own throwaway test channel.

Governance lives in [`.specify/memory/constitution.md`](.specify/memory/constitution.md); the
full spec/plan/tasks are under [`specs/001-podcast-ops-slice/`](specs/001-podcast-ops-slice/).

## Install

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e .            # core (reads + mock spine + tests)
pip install -e ".[live]"    # add Google/Spotify SDKs for real API calls
pip install -e ".[dev]"     # pytest, ruff, black
```

Copy `.env.example` to `.env` (untracked) and fill in credentials when running against live
APIs. Secrets never belong in source control.

## Run the spine

```bash
podcast-ops auth            # one-time: OAuth consent -> secrets/youtube_token.json (write only)
podcast-ops check-access     # M0 gate: confirm the one read + one write are permitted
podcast-ops ingest          # DATA: read both platforms -> run/staging/
podcast-ops fuse            # DATA: resolve + conform -> run/objects/episodes.json
podcast-ops decide          # LOGIC: apply the one rule
podcast-ops act             # ACTION: mock by default ("would publish X to Y")
podcast-ops act --real      # ACTION: real writeback to the test channel (idempotent)
podcast-ops run             # full spine (add --real for the real writeback)
```

`check-access` must pass before modeling/running against real data (constitution Principle V).
The mock spine runs with no credentials and makes zero external calls.

## Architecture (mirrors the three stages)

```
src/podcast_ops/
  ingest/    DATA: YouTube/Spotify gateways (Adapter) + StagingRepository
  resolve/   DATA: Matcher (Strategy) + conform -> Episode objects
  objects/   Episode model + EpisodeRepository
  logic/     the one read-only decision rule (pure function)
  action/    WritebackPort + MockWriteback + YouTubeWriteback + audit log
  commands/  one handler per stage; cli.py is a thin dispatcher
```

External boundaries (platform reads, the writeback) are ports with injected dependencies, so the
whole spine is testable without network.

## Tests

```bash
pytest                 # all
pytest tests/unit      # matcher + decision rule
pytest tests/contract  # gateway response-shape mapping (fixtures)
pytest tests/integration  # mock-mode spine + writeback safety/idempotency
```
