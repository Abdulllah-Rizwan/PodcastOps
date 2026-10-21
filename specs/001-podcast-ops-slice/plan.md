# Implementation Plan: Podcast Ops-Hub Validation Slice

**Branch**: `001-podcast-ops-slice` | **Date**: 2026-10-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-podcast-ops-slice/spec.md`

## Summary

Prove one end-to-end spine of the **data → logic → action** pattern: read public metadata
for one real show from YouTube + Apple Podcasts into a staging area, resolve/conform it into fused
`Episode` objects (the entity-resolution proof), run exactly one read-only decision rule, and
execute exactly one safe, logged, mock-first writeback to our own throwaway YouTube test
channel. Technical approach: a small single Python project with clean seams between the four
stages — platform gateways (Adapter) feed a staging Repository, a Strategy-based matcher
produces `Episode` objects, a pure decision function decides, and a writeback port with a mock
and a real adapter acts. Access for the one read and the one write is confirmed at M0 before
any object is modeled.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**:
- `google-api-python-client` + `google-auth-oauthlib` — YouTube Data API v3 (public reads via
  API key; owned-channel writes via OAuth 2.0)
- `httpx` — Apple Podcasts public iTunes lookup API (no auth; replaced Spotify, see decisions.md)
- `pydantic` v2 — typed object modeling / validation for staging records and `Episode` objects
- `rapidfuzz` — string similarity for entity-resolution matching
- `pytest` — testing

**Storage**: Local JSON files under a run directory — `staging/` for raw platform records and
`objects/` for fused `Episode` objects. No database; a slice that runs once does not need one.

**Testing**: `pytest` — unit tests for the matcher and the decision rule, integration test for
the mock-mode spine, contract tests for the gateway response shapes (recorded fixtures).

**Target Platform**: Local CLI, run on the developer machine (Windows dev environment).

**Project Type**: Single project (CLI orchestrating the four-stage spine).

**Performance Goals**: N/A — one show, run once. Stay within free API quotas (YouTube Data API
default 10,000 units/day; Apple iTunes lookup is unauthenticated, used sparingly). Correctness,
not throughput, is the goal.

**Constraints**:
- Reads use public metadata only (+ YouTube public engagement counts); no owner-only data.
- Writeback targets ONLY our own test channel, is mock-first, safe (retryable), and logged.
- Secrets (API keys, OAuth tokens) via environment / local untracked config — never committed.

**Scale/Scope**: One show; on the order of tens to a few hundred episodes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gates derived from `.specify/memory/constitution.md` (v1.1.0):

| # | Principle | Gate | Initial |
|---|-----------|------|---------|
| I | Narrow Slice, Ship-Not-Learn | Plan builds only the single spine; no extra platform, model, dashboard, loop, or generality. | ✅ PASS |
| II | Data → Logic → Action Separation | Four distinct components; raw→staging→resolve→object; logic read-only; only the action mutates the world. | ✅ PASS |
| III | Entity Resolution Is the Hard Core | A real, inspectable matcher (normalize + multi-signal + fuzzy) with unit tests; no exact-equality shortcut. | ✅ PASS |
| IV | Safe, Logged, Mock-First Writeback | Writeback behind a port; mock mode logs "would publish X to Y"; real mode test-channel-only, retryable, logged. | ✅ PASS |
| V | Confirm API Access Before Modeling | M0 research (research.md) confirms the one read + one write before data-model.md is acted on. | ✅ PASS |
| VI | High Code Quality & Design Discipline | Adapter/Gateway, Repository, Strategy, port/seam; dependency inversion for mockability; tests; no secrets committed; YAGNI. | ✅ PASS |

No violations. Complexity Tracking left empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-podcast-ops-slice/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── youtube-read.md
│   ├── apple-read.md
│   └── youtube-writeback.md
├── spec.md              # Feature spec (/speckit-specify)
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks output (NOT created here)
```

### Source Code (repository root)

```text
src/podcast_ops/
├── config.py                 # env-based config; no secrets in source
├── ingest/                   # DATA (read + stage) — Adapter/Gateway + staging Repository
│   ├── youtube_gateway.py    #   reads YouTube public metadata + engagement counts
│   ├── apple_gateway.py      #   reads Apple Podcasts public episode metadata (iTunes lookup)
│   └── staging.py            #   StagingRepository: raw records land here first
├── resolve/                  # DATA (resolve + conform) — entity resolution → objects
│   ├── matcher.py            #   Strategy: match episodes across platforms (the hard core)
│   └── conform.py            #   build conformed Episode objects from matched records
├── objects/                  # the fused object layer
│   ├── episode.py            #   Episode object model (pydantic)
│   └── repository.py         #   EpisodeRepository (JSON-backed)
├── logic/                    # LOGIC (decide) — read-only
│   └── decision.py           #   the one rule: pure function over Episode objects
├── action/                   # ACTION — the only thing that changes the world
│   ├── writeback.py          #   WritebackPort + MockWriteback + YouTubeWriteback
│   └── audit_log.py          #   logs every attempt (mock/real, success/failure)
└── cli.py                    # orchestrates the spine; --mock / --real flag

tests/
├── unit/                     # matcher + decision rule
├── integration/              # full spine in mock mode
└── contract/                 # gateway response-shape tests against recorded fixtures
```

**Structure Decision**: Single Python project. Directory boundaries mirror the constitution's
data → logic → action stages exactly (`ingest` + `resolve`/`objects` = data, `logic` = decide,
`action` = act), satisfying Principle II structurally and Principle VI's separation-of-concerns
requirement. External boundaries (platform gateways, writeback) are ports with adapters so they
are mockable (Principle IV, VI).

## Complexity Tracking

> No constitution violations — section intentionally empty.
