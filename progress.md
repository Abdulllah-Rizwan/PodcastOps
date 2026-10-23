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

- **Phase**: 🚀 **PIVOTED — building the ontology engine** (2026-10-23). The original narrow validation slice is **complete and proven** (2026-10-21, commit `bcc5502`); the project has been deliberately redefined into a reusable, **AI-native ontology engine proven by verticals** (constitution MAJOR bump **1.1.0 → 2.0.0**). Podcast ops = **vertical #1** (the live demo). See `decisions.md` (2026-10-23).
- **Active feature**: `specs/002-ontology-engine` — the full-stack engine. Its **full Spec Kit cycle is complete**: `spec.md` + requirements checklist (`/speckit-specify`), `plan.md` + `research.md` + `data-model.md` + `contracts/` + `quickstart.md` (`/speckit-plan`), and `tasks.md` with **66 tasks** (`/speckit-tasks`). `specs/001-podcast-ops-slice` remains the *completed* slice.
- **Current milestone**: **M0 skeleton built** (Phases 1–2 of `002`, tasks T001–T026 done). The monorepo (`engine/`, `verticals/podcast/`, `apps/api`, `apps/web`, `infra/`), engine core (ontology model, ports, JSON + Postgres repositories, registry, config), the podcast vertical (Show/Episode/Guest/Clip + YouTube/Apple adapters, registered through the engine), and the FastAPI `/health` app all exist; **10 M0 smoke tests pass, ruff + black clean**. The old slice's M0–M3 are satisfied and folded in; its proven Python core seeds the engine.
- **Decided direction**: engine-is-the-product; generality *earned* by a second vertical (M5), never asserted. Full-stack: web UI (ontology explorer + ops dashboard + AI agent), FastAPI backend over the existing Python core, Postgres + **pgvector**, background worker, AI layer grounded in the ontology, eval + observability harness, cloud (default: GCP Cloud Run + Vercel).
- **Carried forward from the slice**: proven YouTube + Apple read, honest entity resolution (`Episode` fusion), the decision-rule pattern, and the safe/mock-first/idempotent/audited writeback seam. The **199 real matched pairs** from the live run seed the entity-resolution golden eval set.
- **Committed & pushed**: slice at commit `bcc5502` on `main` → `github.com/Abdulllah-Rizwan/PodcastOps`. The pivot checkpoint — governance docs (constitution v2.0.0, CLAUDE.md, decisions.md, this file) **plus** the complete `specs/002-ontology-engine/` planning cycle (spec + plan + tasks) — is **committed and pushed to `main`** as of 2026-10-23. No secrets committed (`.env`, `secrets/`, `run/` gitignored).
- **Next action**: continue `/speckit-implement` at **Phase 3 (US1 — see the fused ontology, the 🎯 MVP)**: baseline matcher + ingest pipeline (resolution tests first), ingest/explorer API endpoints, and the explorer UI. **26/66 tasks done (T001–T026)**; 40 remain. Decided plumbing defaults (pgvector, Cloud Run/Vercel) are baked into the plan; confirm/override during implementation.
- **Note on the slice**: the proven `src/podcast_ops/` is deliberately **kept alongside** the new `engine/` + `verticals/podcast/` packages (migrate-by-copy-and-generalize), so vertical #1 stays runnable end-to-end (Principle I) until the engine reaches parity in US1–US3; `src/` is retired then.
- **Blockers**: None.
- **Live run config (from the slice, still valid for vertical #1)**: Huberman Lab — `TARGET_YOUTUBE_SOURCE=UC2D2CMWXMOVWx7giW1n3LIg`, `TARGET_APPLE_SHOW=1545953110`, write target `TEST_VIDEO_ID=CfRIjrzeGrU`.

### Milestone tracker (re-baselined to constitution v2.0.0)

| Milestone | Description | Status |
|-----------|-------------|--------|
| M0 | Full-stack skeleton: API over existing core, Postgres, minimal UI, deployed thin (no AI yet) | 🏗️ Skeleton built (Phases 1–2, T001–T026); deploy-thin at Phase 7 |
| M1 | Generalized ontology core: declarative object/link/function/action registries; podcast as a vertical plugin | ⬜ |
| M2 | Entity resolution upgraded (embeddings + vector store) + precision/recall evals vs golden set | ⬜ |
| M3 | AI agent over the ontology: grounded retrieval + answers; proposes validated, audited, human-approved actions; AI evals + tracing | ⬜ |
| M4 | Harden & deploy for real: CI/CD eval gate, observability, secrets, autoscale; UI complete | ⬜ |
| M5 | Vertical #2: a second domain on the same engine, no engine rewrite — the generality proof | ⬜ |

**Prior (slice) milestones — all ✅ done 2026-10-21, folded into the above:** M0 access gate (3/3), M1 fuse (541 YouTube + 200 Apple → 542 Episodes, 199 matched), M2 one decision rule, M3 mock-then-real `videos.update` to `CfRIjrzeGrU` (idempotent, audited).

---

## History (newest first)

### 2026-10-23 (latest) — M0 skeleton implemented (`002` Phases 1–2, T001–T026)

- Ran `/speckit-implement` scoped to the M0 full-stack skeleton (Phase 1 Setup + Phase 2
  Foundational), stopping before US1.
- **Phase 1 (T001–T009)**: created the monorepo (`engine/`, `verticals/podcast/`, `apps/api`,
  `apps/web`, `infra/{docker,deploy,migrations}`, `.github/workflows`), the three Python package
  `pyproject.toml`s, a hand-scaffolded Next.js app (explorer/ops/evals/agent routes stubbed),
  `docker-compose` (postgres+pgvector, redis, langfuse) + API Dockerfile, extended `.env.example`
  + `.gitignore`/`.dockerignore`, ruff/black + ESLint/Prettier config, and a CI skeleton
  (lint + test jobs; eval-gate/deploy deferred to T049/T060–T061).
- **Phase 2 (T010–T026)**: engine core — ontology model (`ObjectType`/`LinkType`/`ObjectInstance`/
  `LinkInstance`), `StagingRecord`, `ResolutionDecision`, the `SourceAdapter`/`Repository`/
  `EmbeddingProvider` ports, `JsonRepository` (hermetic) + `PostgresRepository` (pgvector, lazy
  SQLAlchemy) + the read-only view, Alembic initial migration, access gate, the `Vertical`
  registry (the engine's only discovery path — no engine→vertical import), and `Settings`. Podcast
  vertical — Show/Episode/Guest/Clip + links, YouTube + Apple adapters (migrated from the slice
  gateways), registered via `vertical_podcast.registry`. FastAPI app with `/health` reporting the
  registered ontology.
- **Verification**: 10 M0 smoke tests pass (engine 6, vertical 3, api 1); the app boots; the
  read-only view exposes no write methods; optional-dep modules import without their SDKs (Principle
  VII). `ruff` + `black` clean across `engine`/`verticals`/`apps/api`.
- **Deliberate deviation logged**: kept `src/podcast_ops/` alongside the new packages so vertical #1
  stays runnable end-to-end until the engine reaches parity (Principle I); see `decisions.md`.
- Next: Phase 3 (US1 MVP — fused ontology visible in the explorer).

### 2026-10-23 (later) — full Spec Kit cycle for `002-ontology-engine` complete; pivot checkpoint committed

- Ran the complete planning cycle for the engine feature: `/speckit-specify` → `spec.md` +
  requirements checklist; `/speckit-plan` → `plan.md`, `research.md`, `data-model.md`,
  `contracts/` (api, engine-ports, agent-tools), `quickstart.md`; `/speckit-tasks` → `tasks.md`
  with **66 tasks** across 7 phases (Setup, Foundational, US1 fused-ontology MVP, US2 decide→approve→act,
  US3 resolution-measured, US4 grounded AI agent, Polish). No constitution violations flagged.
- **Session-recovery note**: the prior session was terminated mid-flight (an unrelated terminal
  `update` command crashed it) *after* `tasks.md` was written but *before* `progress.md`/`decisions.md`
  were refreshed — so this file had wrongly still listed `/speckit-specify` as the next action. On
  resume, verified all `specs/002-ontology-engine/` artifacts are intact (none truncated) and that
  **no implementation had started** (0/66 tasks, `src/` untouched since the slice).
- Committed and pushed the pivot checkpoint to `main`: governance docs (constitution v2.0.0,
  CLAUDE.md, decisions.md, this file) + the entire `specs/002-ontology-engine/` planning cycle.
- Next: `/speckit-implement` — Phase 1–2 (M0 skeleton) then US1 MVP.

### 2026-10-23 — PIVOT: narrow slice → reusable AI-native ontology engine

- The completed slice proved the data → logic → action spine. Owner decided the valuable asset is
  the **engine / ontology pattern itself**, not a single podcast app — so the project is redefined
  into a reusable, AI-native **ontology engine proven by verticals** (podcast = vertical #1; a
  second vertical later = the generality proof). Learning-by-building + showcasing full-stack/AI
  expertise are the explicit goals; a usable tool / possible product are secondary.
- Governance done this session: constitution amended **1.1.0 → 2.0.0** (MAJOR — reverses the former
  bans on a general engine, on ML/AI, and on "runs once / not a product"; adds *Engine First,
  Proven by Verticals* and *AI Grounded in the Ontology, and Evaluated*; keeps stage separation,
  entity-resolution-is-the-hard-core, safe/mock-first actions, confirm-access, code quality).
  `CLAUDE.md` rewritten to the engine direction; `decisions.md` pivot entry added; this file
  re-baselined (milestones M0–M5 redefined).
- Guardrail carried forward: **generality is earned by vertical #2, never asserted** — build
  vertical-shaped first with clean seams; no abstractions a current vertical doesn't use.
- Next: `/speckit-specify` the full-stack engine scope (running now), then `/speckit-plan` and
  `/speckit-tasks`. Governance doc changes not yet committed.

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
- Committed (`bcc5502`) and pushed to `main`. **Session paused here — next session decides the
  project's direction** (M4 loop / M5 widen / harden); see "Next action" above.

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
