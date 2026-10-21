# Progress Log — Podcast Ops-Hub

**Purpose**: The single place a fresh session reads first to know **where we are and what to
pick up next**. Keep it current: update the "Current Status" block and add a dated entry
whenever a meaningful step completes.

**Read-first order for a new session**:
1. `CLAUDE.md` — project constitution-in-brief and guardrails
2. `.specify/memory/constitution.md` — full constitution (principles + scope boundaries)
3. `progress.md` (this file) — where we are
4. `decisions.md` — any deviations from plan
5. `specs/001-podcast-ops-slice/` — spec, and (once created) plan.md / tasks.md

---

## Current Status

- **Phase**: ✅ **SLICE COMPLETE** (2026-10-21). Full data → logic → action spine ran end-to-end on live data with a real, safe, logged, idempotent writeback to the test channel. Definition of Done met. 32/32 tasks done; 16/16 tests pass; lint/format clean.
- **Active feature**: `specs/001-podcast-ops-slice` (the full data → logic → action validation slice).
- **Current milestone**: **M0, M1, M2, M3 all done** (live). M4 (loop) and M5 (widen) remain deferred per the constitution — not part of this slice.
- **Decided stack**: Python 3.11+, JSON-file storage, YouTube Data API v3 (read via API key / write via OAuth to test channel), **Apple Podcasts via the public iTunes lookup API (read, no auth)** — replaced Spotify on 2026-10-21, see `decisions.md`. Writeback = `videos.update` show-notes on our test channel; rule = "on Apple Podcasts, no YouTube clip yet".
- **Next action**: None required to finish the slice — it is done. Optional follow-ups only: the deferred milestones M4 (close one loop) and M5 (widen), which are explicitly out of scope for this validation slice.
- **Blockers**: None.
- **Live run config (2026-10-21)**: Huberman Lab — `TARGET_YOUTUBE_SOURCE=UC2D2CMWXMOVWx7giW1n3LIg`, `TARGET_APPLE_SHOW=1545953110`, write target `TEST_VIDEO_ID=CfRIjrzeGrU`.

### Milestone tracker (from the constitution)

| Milestone | Description | Status |
|-----------|-------------|--------|
| M0 | Confirm API access for the one read and the one write | ✅ Done — gate PASSED 3/3 live (YouTube read, Apple read, YouTube write scope) |
| M1 | Read + fuse both platforms into `Episode` objects (entity resolution) | ✅ Done — live: 541 YouTube + 200 Apple → 542 Episodes, 199 two-sided matched |
| M2 | One function produces a decision | ✅ Done (rule + tests; live: selected 1 Apple-only episode) |
| M3 | One action: mock-logged first, then real against test channel, safe + logged | ✅ Done — mock then real `videos.update` to `CfRIjrzeGrU`; retry `skipped_idempotent`; all logged |
| M4 | _(later)_ Close one loop | ⬜ Deferred |
| M5 | _(later)_ Widen | ⬜ Deferred |

---

## History (newest first)

### 2026-10-21 (latest) — SLICE COMPLETE: live end-to-end run (T031, Definition of Done)

- Operator chose **Huberman Lab**; filled `.env` with channel `UC2D2CMWXMOVWx7giW1n3LIg`,
  Apple show `1545953110`, test video `CfRIjrzeGrU`.
- Installed the missing `google-auth-oauthlib` dep; ran `podcast-ops auth` → minted the
  `youtube.force-ssl` write token to `secrets/youtube_token.json`.
- `check-access`: **gate PASSED 3/3** (YouTube read, Apple read, YouTube write scope).
- `run` (mock): ingest 541 YouTube + 200 Apple → fuse 542 Episodes (199 two-sided matched,
  entity resolution working on real data) → rule selected 1 Apple-only episode → mock logged.
- `run --real`: same spine, **real** `videos.update` appended the show-notes marker to
  `CfRIjrzeGrU` → `success`. `act --real` again → `skipped_idempotent` (no duplicate). All three
  attempts in `run/action/audit.log`. **SC-001..SC-006 satisfied — Definition of Done met.**
- Marked T031 `[X]`; 32/32 tasks complete.

### 2026-10-21 (later) — switched second read platform Spotify → Apple Podcasts

- Spotify Web API returned HTTP 403 on **every** endpoint for the operator's app:
  *"Active premium subscription required for the owner of the app."* Confirmed not show-,
  market-, or code-specific (probed famous show IDs, markets US/PK/none, plus artist + search).
  A hard external blocker — Principle V could not pass.
- Operator chose to **switch to Apple Podcasts** (free, public iTunes lookup API, no auth).
- Refactored the read side: new `ingest/apple_gateway.py` (replaces `spotify_gateway.py`),
  `Platform` enum `spotify`→`apple`, `Episode.apple` ref, rule `apple_without_youtube`,
  `access_check.check_apple_read`, dropped Spotify creds from `config`, `TARGET_APPLE_SHOW` env.
  Updated tests + fixtures (`apple_episodes.json`, `test_apple_read.py`). **16/16 tests pass,
  ruff + black clean.** Live Apple read verified end-to-end against a real show.
- Governance: constitution amended **1.0.0 → 1.1.0**; `decisions.md` deviation entry added;
  `contracts/apple-read.md` added (replaces `spotify-read.md`); docs updated.
- Next: operator fills `.env` (now `TARGET_APPLE_SHOW`, no Spotify creds), runs `auth`,
  `check-access`, then `run --real` (T031).

### 2026-10-21

- Drafted and ratified the project constitution → `.specify/memory/constitution.md` (v1.0.0),
  including the high-code-quality / design-patterns principle.
- Ran `/speckit-specify` → created feature `001-podcast-ops-slice` with `spec.md` and the
  requirements quality checklist (all checklist items pass).
- Created `decisions.md` (deviation log) and `progress.md` (this file).
- Ran `/speckit-plan` → `plan.md`, `research.md` (Phase 0 + M0 access checklist), `data-model.md`,
  `contracts/` (youtube-read, spotify-read, youtube-writeback), `quickstart.md`. Constitution
  check passed before and after design (no violations).
- Ran `/speckit-tasks` → `tasks.md`: 32 tasks across Setup, Foundational (incl. M0 gate T011),
  US1 fuse, US2 decide, US3 act, and Polish. Tests included (constitution-mandated).
- Ran `/speckit-implement` → built the full Python package under `src/podcast_ops/` (config,
  ingest gateways + staging, matcher + conform, Episode objects + repo, decision rule, writeback
  port + mock + real + audit log, CLI + command handlers), plus `pyproject.toml`, `.gitignore`,
  `.env.example`, `README.md`. Added hermetic test suite (`tests/`): 16 tests, all passing.
  Lint (ruff) and format (black) clean. Smoke-ran the mock spine end-to-end successfully.
  Marked 31/32 tasks `[X]`; T031 (real end-to-end run) left open — blocked on operator creds.
- Next: operator supplies `.env` + test channel, runs `check-access` then `run --real` (T031).
