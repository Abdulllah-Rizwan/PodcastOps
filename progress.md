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

> ### ⏸️ STOPPED FOR THE DAY — 2026-10-24 (end of day). START HERE TOMORROW (2026-10-25):
> **Where we are:** Phase 7 **local** tasks are done. US1–US4 + the Phase 7 local work are built, committed, and pushed to `main` (HEAD `e3d7680`, plus this end-of-day docs commit). **63/66 tasks done** (T059, T060, T061, T064, T066 landed today), M0–M3 complete + M4 partially built, **61 tests pass hermetically, ruff + black clean**. Working tree clean after the docs commit.
>
> **Only 3 tasks remain — all credential/deploy-gated: T062, T063, T065.** Tomorrow is mostly *account setup* (GCP + Neon + Voyage + Anthropic key), then the live check and deploy.
>
> **Decisions locked today** (confirmations of planned defaults, so not deviation-log entries): DB host = **Neon** (Postgres + pgvector); embeddings = **Voyage** (`EMBEDDING_PROVIDER=voyage`, needs `VOYAGE_API_KEY`); agent stays on **Claude** (needs separate **API credits** — Claude Pro does **not** grant API access; a free-LLM adapter was offered and **deferred**).
>
> **DO FIRST TOMORROW — T062 needs NO new setup (YouTube creds already in `.env` + `secrets/`):**
> run the live `GET /access/check` against the real show (Huberman) and confirm **3/3** (YouTube read, Apple read, YouTube write scope). Start the API (`uvicorn app.main:app --app-dir apps/api/src`) and hit `/access/check`, or call the engine access module directly. If the YouTube OAuth token has expired (minted 2026-10-21), re-run the auth consent to refresh `secrets/youtube_token.json`.
>
> **THEN — account setup the user is doing tomorrow (see `infra/deploy/README.md` for exact commands):**
> 1. **Neon** — create project, `CREATE EXTENSION vector;`, copy connection string → `DATABASE_URL`.
> 2. **Voyage** — get `VOYAGE_API_KEY`; keep `EMBEDDING_PROVIDER=voyage`.
> 3. **Anthropic** — buy API credits at console.anthropic.com, get `ANTHROPIC_API_KEY` (Pro ≠ API).
> 4. **GCP** — project + billing; enable run/artifactregistry/secretmanager/cloudscheduler APIs; Artifact Registry repo; Secret Manager secrets (one per row in `infra/deploy/README.md`); run the Alembic migration against Neon.
> 5. **CI deploy** — set GitHub repo vars `DEPLOY_ENABLED=true`, `GCP_PROJECT_ID`, `GCP_REGION` + secrets `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SA` (Workload Identity Federation). Until `DEPLOY_ENABLED=true`, the deploy job stays dormant.
> 6. **Vercel** — import repo, Root Directory = `apps/web`, set `NEXT_PUBLIC_API_BASE_URL` to the Cloud Run URL.
>
> **THEN — T063** (the SC-006 live spine + M4 Definition of Done): deploy (CI does the build/push + Cloud Run deploy once the vars are set), then run `specs/002-ontology-engine/quickstart.md` Scenarios 1–4 against the deployed stack on Huberman Lab; capture the audit trail. **T065**: mark M4 built here + log any deviations in `decisions.md`.
>
> **Verify the baseline before starting (should be green):**
> `PYTHONPATH="engine/src;verticals/podcast/src;apps/api/src" python -m pytest engine/tests verticals/podcast/tests apps/api/tests` → **61 passed**. (Bare `pytest` under-collects; name the three roots — see the known test-discovery note below.)
>
> **Known follow-ups to fold in opportunistically (already logged):** adapters emit `duration_seconds` but the episode type/matcher expect `duration_s` (duration signal inert — fix when wiring live ingest in T062/T063); `traverse` returns no neighbors until `LinkInstance`s are materialized; `/agent/ask` is JSON not SSE streaming; add `testpaths` to `pyproject`/`pytest.ini` so bare `pytest` collects all 3 roots; the agent layer is Anthropic-bound in `ai/agent.py` (tools/propose are provider-neutral) — extract an `Agent` port + free-LLM adapter if a non-Claude demo is wanted.

- **Phase**: 🚀 **PIVOTED — building the ontology engine** (2026-10-23). The original narrow validation slice is **complete and proven** (2026-10-21, commit `bcc5502`); the project has been deliberately redefined into a reusable, **AI-native ontology engine proven by verticals** (constitution MAJOR bump **1.1.0 → 2.0.0**). Podcast ops = **vertical #1** (the live demo). See `decisions.md` (2026-10-23).
- **Active feature**: `specs/002-ontology-engine` — the full-stack engine. Its **full Spec Kit cycle is complete**: `spec.md` + requirements checklist (`/speckit-specify`), `plan.md` + `research.md` + `data-model.md` + `contracts/` + `quickstart.md` (`/speckit-plan`), and `tasks.md` with **66 tasks** (`/speckit-tasks`). `specs/001-podcast-ops-slice` remains the *completed* slice.
- **Current milestone**: **M0 + US1 (fused ontology) + US2 (decide → approve → act) + US3 (resolution, measured) + US4 (grounded, propose-only agent) built** (Phases 1–6 of `002`, tasks T001–T058 done). US4 adds the AI layer: side-effect-free grounded retrieval tools (`search_objects`/`get_object`/`traverse`/`run_function`), the agent on Claude Opus 5.5 via the SDK Tool Runner (grounding context under `cache_control: ephemeral`, adaptive thinking) returning a `GroundedAnswer` (answer + citations to real object ids + proposed actions + `trace_id`), the `propose_action` tool (validates against the ActionDef + owned-target policy, mock-previews, and **never** executes), a Langfuse tracing seam (no-op default), the `/agent/ask` + `/agent/proposals/{id}/approve` endpoints (approve routes through the human-approved execute path), and the agent chat UI. The `anthropic` SDK is lazy-imported so the engine imports without it, and `/agent/ask` returns 503 when no API key is set — so **50 tests pass hermetically; ruff + black clean**. US3 adds the similarity (`HashingEmbeddings` cosine) + combined matchers (baseline stays runnable alone, Principle III), the ER eval harness (precision/recall/F1 + mismatch list + JSON report) over a golden set of **199 real matched pairs + 116 curated hard negatives**, a **hermetic CI gate** (`eval-gate` job fails the build if precision < 95% or recall < 90%), and the `/evals/resolution/*` API + eval-dashboard UI. **Baseline scores P = R = 1.000 on the 315-case golden set; 41 tests pass; ruff + black clean.** On top of US1, US2 adds the read-only function-execution service (functions get a `ReadOnlyStore` only — read-only by the handle, not convention) + the `apple_without_youtube` decision rule; the safe Action port (`preview`→mock logs intent + no external call; `execute`→real, refuses unless `approved=true` **and** write-access confirmed, computes an idempotency key, returns `skipped_idempotent` on repeat, persists **every** attempt via an `AuditTrail`) + the `youtube_update_show_notes` writeback (owned-test-channel-only, idempotent on marker, injected transport); the functions/actions API (`GET /functions`, `POST /functions/{key}/run`, `GET /actions`, `POST /actions/{key}/preview`, `POST /actions/{key}/execute`, `GET /actions/attempts`); and the ops dashboard UI (flagged episodes → mock preview → approve + execute → audit timeline). **32 tests pass (incl. decision read-only + full action-seam contract + actions API), ruff + black clean.** The old slice's M0–M3 are satisfied and folded in; its proven Python core seeds the engine.
- **Decided direction**: engine-is-the-product; generality *earned* by a second vertical (M5), never asserted. Full-stack: web UI (ontology explorer + ops dashboard + AI agent), FastAPI backend over the existing Python core, Postgres + **pgvector**, background worker, AI layer grounded in the ontology, eval + observability harness, cloud (default: GCP Cloud Run + Vercel).
- **Carried forward from the slice**: proven YouTube + Apple read, honest entity resolution (`Episode` fusion), the decision-rule pattern, and the safe/mock-first/idempotent/audited writeback seam. The **199 real matched pairs** from the live run seed the entity-resolution golden eval set.
- **Committed & pushed**: slice at commit `bcc5502` on `main` → `github.com/Abdulllah-Rizwan/PodcastOps`. The pivot checkpoint — governance docs (constitution v2.0.0, CLAUDE.md, decisions.md, this file) **plus** the complete `specs/002-ontology-engine/` planning cycle (spec + plan + tasks) — is **committed and pushed to `main`** as of 2026-10-23. No secrets committed (`.env`, `secrets/`, `run/` gitignored).
- **Next action**: **T062 first (no setup needed)** — run the live `GET /access/check` on the real show; then the user sets up Neon + Voyage + Anthropic + GCP + Vercel (see the START-HERE block above and `infra/deploy/README.md`) and we do **T063** (deploy + live E2E on Huberman, the SC-006 spine + M4 DoD) and **T065** (mark M4 built). **63/66 tasks done (T001–T061, T064, T066)**; 3 remain (T062, T063, T065). The explorer/ops/eval/agent UIs are coded but still only exercised hermetically — their first live run is T063.
- **Note on the slice**: the proven `src/podcast_ops/` is deliberately **kept alongside** the new `engine/` + `verticals/podcast/` packages (migrate-by-copy-and-generalize), so vertical #1 stays runnable end-to-end (Principle I) until the engine reaches parity in US1–US3; `src/` is retired then.
- **Blockers**: None.
- **Live run config (from the slice, still valid for vertical #1)**: Huberman Lab — `TARGET_YOUTUBE_SOURCE=UC2D2CMWXMOVWx7giW1n3LIg`, `TARGET_APPLE_SHOW=1545953110`, write target `TEST_VIDEO_ID=CfRIjrzeGrU`.

### Milestone tracker (re-baselined to constitution v2.0.0)

| Milestone | Description | Status |
|-----------|-------------|--------|
| M0 | Full-stack skeleton: API over existing core, Postgres, minimal UI, deployed thin (no AI yet) | 🏗️ Skeleton built (Phases 1–2, T001–T026); deploy-thin at Phase 7 |
| M1 | Generalized ontology core: declarative object/link/function/action registries; podcast as a vertical plugin | ✅ Done — object/link/source registries + resolution pipeline (US1, T027–T036) and function/action registries + safe-action port (US2, T037–T044); podcast is a plugin via `Vertical`/`OntologyRegistry` |
| M2 | Entity resolution upgraded (embeddings + vector store) + precision/recall evals vs golden set | ✅ Done (eval side) — similarity + combined matchers, golden set (199 real pairs + 116 hard negatives), precision/recall/F1 harness + hermetic CI gate (US3, T045–T051). Baseline P=R=1.000. Live pgvector-backed similarity ingest is wired but exercised only hermetically until Phase 7 deploy (T062–T063) |
| M3 | AI agent over the ontology: grounded retrieval + answers; proposes validated, audited, human-approved actions; AI evals + tracing | ✅ Done — grounded tools + Opus-5.5 Tool Runner agent returning GroundedAnswer (citations to real ids), propose-only (`propose_action` never executes), Langfuse tracing seam, deterministic AI evals + guarded Haiku judge, `/agent/*` endpoints + chat UI (US4, T052–T058). Live answers need an `ANTHROPIC_API_KEY`; graceful 503 without one |
| M4 | Harden & deploy for real: CI/CD eval gate, observability, secrets, autoscale; UI complete | 🏗️ Partial — **local** Phase 7 done (T059 seam guard, T060 Neon/Cloud Run/Vercel deploy config, T061 gated CI build+deploy job, T064 README, T066 security pass). Remaining: live access check (T062), deploy + live E2E on the real show (T063), M4 sign-off (T065) — all credential/account-gated |
| M5 | Vertical #2: a second domain on the same engine, no engine rewrite — the generality proof | ⬜ |

**Prior (slice) milestones — all ✅ done 2026-10-21, folded into the above:** M0 access gate (3/3), M1 fuse (541 YouTube + 200 Apple → 542 Episodes, 199 matched), M2 one decision rule, M3 mock-then-real `videos.update` to `CfRIjrzeGrU` (idempotent, audited).

---

## History (newest first)

### 2026-10-24 — Phase 7 local tasks done (seam guard, security, deploy config, CI deploy); M4 partial

- Resumed at Phase 7 and completed all **local** (credential-free) tasks, in the recommended order:
  - **T059** — engine/vertical seam guard `engine/tests/test_engine_vertical_seam.py`: AST scan asserts
    no `engine/` module imports a vertical, plus a `vertical_podcast` string guard (SC-005).
  - **T064** — rewrote `README.md` for the ontology engine: engine-vs-vertical seam, the
    data→logic→action→AI story with an ASCII architecture diagram, run/deploy, status.
  - **T066** — security pass as executable tests: `engine/tests/test_security_posture.py` (gitignore +
    no tracked secrets; `execute` refuses without approval; the whole `ai/` layer has **zero** `.execute(`
    calls; `propose_action` only mock-previews) and `verticals/podcast/tests/test_security_owned_target.py`
    (writeback refuses any channel but the owned test channel).
  - **T060** — Neon-based deploy config in `infra/deploy/` (`cloud-run-api.yaml`, `cloud-run-ingest-job.yaml`,
    `vercel.json`, runbook `README.md`) + a one-shot `apps/api/src/app/jobs.py` ingest entrypoint
    (`python -m app.jobs`) for the Cloud Run Job, reusing the same `execute_ingestion` callable as the API/worker.
  - **T061** — added the gated `build-and-deploy` job to `.github/workflows/ci.yml` (build/push image +
    `gcloud run` deploy of the service and job), `needs: [lint, test, eval-gate]`, dormant until repo var
    `DEPLOY_ENABLED=true`.
- **Verification: 61 tests pass hermetically** (was 50; +11 new), ruff + black clean across 82 files; CI and
  both Cloud Run manifests parse as valid YAML; `app.jobs` imports.
- Committed + pushed to `main` as `e3d7680` (Phase 7 local) plus this end-of-day docs commit.
- **Decisions locked (planned defaults, not deviations):** Neon for Postgres+pgvector; Voyage for embeddings
  (`EMBEDDING_PROVIDER=voyage`); agent stays on Claude (API credits required — **Claude Pro grants no API
  access**; a free-LLM adapter was offered and deferred — the agent is Anthropic-bound only in `ai/agent.py`,
  while `ai/tools.py` + `ai/propose.py` are provider-neutral).
- **Clarified** that pgvector *stores/searches* vectors but does not *generate* them — an embedding model
  (Voyage / local / hashing) is still needed to produce them; and that GCP provides compute/secrets, not the
  database, so Neon is the single Postgres host (no second DB).
- **M4 is now partial** (local done). **63/66 tasks; 3 remain — all account/deploy-gated: T062, T063, T065.**
- **Tomorrow (2026-10-25):** T062 first (no setup — YouTube creds already present), then the user sets up
  Neon/Voyage/Anthropic/GCP/Vercel (see the START-HERE block + `infra/deploy/README.md`), then T063 (deploy +
  live E2E on Huberman) and T065 (M4 sign-off).

### 2026-10-23 (end of day) — STOP for the day; US1–US4 done and pushed

- Stopped development for 2026-10-23. State: **58/66 tasks (T001–T058)**, milestones **M0–M3 complete**,
  US1–US4 all built, committed, and pushed to `main` (HEAD `92f6207`). Working tree clean.
- Latest four commits on `main`: `92f6207` US4, `334eda7` US3, `1ec77bb` US2, `01a7406` US1.
- **50 tests pass hermetically; ruff + black clean; engine imports without optional deps
  (anthropic / voyageai / sqlalchemy / sentence-transformers).** No live external calls in the suite.
- **Tomorrow (2026-10-24): resume at Phase 7 (T059–T066)** — see the "START HERE TOMORROW" block at the
  top of Current Status for the exact order (local tasks T059/T064/T066/T060/T061 first, then confirm
  credentials with the user before the live/deploy tasks T062/T063/T065).

### 2026-10-23 (US4) — US4 implemented: grounded, propose-only AI agent (`002` Phase 6, T052–T058)

- Ran `/speckit-implement` for Phase 6 (US4), AI-eval test first (T052).
- **Grounded tools** (T053, `ai/tools.py`): `search_objects`, `get_object`, `traverse`, `run_function`
  — side-effect-free reads over a `ReadOnlyStore`, returning real object ids so answers are citable.
  (`traverse` reports available link types but no neighbors yet — LinkInstances aren't materialized.)
- **Agent** (T054, `ai/agent.py`): Claude Opus 5.5 via the SDK Tool Runner
  (`client.beta.messages.tool_runner`), grounding context under `cache_control: ephemeral`, adaptive
  thinking; returns a `GroundedAnswer(answer_text, citations[], proposed_actions[], trace_id)`.
  Citations are the real ids the tools returned, so each resolves to an ObjectInstance by construction.
- **propose_action** (T055, `ai/propose.py`): validates inputs against the ActionDef + owned-target
  policy, records an `ActionProposal` with a **mock** preview; it never calls the Action port's
  `execute` (Principle IV). A human approves via the API.
- **Tracing** (T056, `ai/tracing.py`): a `trace()` seam; no-op tracer (still mints a `trace_id`) by
  default, Langfuse adapter lazy-imported when configured.
- **API** (T057, `routers/agent.py`): `POST /agent/ask` (503 without an API key) +
  `POST /agent/proposals/{id}/approve` (routes through the same human-approved `ActionExecutor.execute`
  path). **UI** (T058, `app/agent/`): chat; citations link to objects; proposals render with an
  explicit approve button.
- **50 tests pass hermetically** (41 prior + 6 AI-eval + 3 agent API); the `anthropic` SDK is
  lazy-imported, so the engine imports and tests run without it; ruff + black clean. **M3 done.**
  Rationale (lazy SDK, propose-only, hermetic evals, deferred streaming/links) logged in `decisions.md`.
  Next: Phase 7 (polish, deploy, live E2E).

### 2026-10-23 (earlier · US3) — US3 implemented: entity resolution, measured + CI-gated (`002` Phase 5, T045–T051)

- Ran `/speckit-implement` for Phase 5 (US3), constitution-mandated eval test first (T045).
- **Matchers** (T047, `resolve/similarity.py`): `SimilarityMatcher` (embedding cosine) + `CombinedMatcher`
  (weighted blend, both signal sets kept for inspectability). The deterministic `BaselineMatcher`
  stays runnable **alone** so upgrades are measured against it (Principle III). Added a pure-Python
  `HashingEmbeddings` provider so the similarity path is hermetic (no model download / network).
- **Golden set** (T046, `evals/golden.py` + `verticals/podcast/evals/golden/cases.jsonl`): seeded from
  the 2026-10-21 live run's **199 real matched pairs** + **116 curated hard negatives** (title-similar
  but date-far — separable by the multi-signal baseline, but a title-only matcher is fooled). Public
  podcast metadata only; no secrets. `GoldenCase` loader with `kind` match|non_match.
- **Eval harness** (T048, `evals/resolution.py`): precision/recall/F1, mismatch list, threshold, JSON
  report; matcher-agnostic; fully hermetic on `JsonRepository`/in-memory cases.
- **CI gate** (T049, `evals/run_gate.py` + `.github/workflows/ci.yml` `eval-gate` job): runs the eval
  and **fails the build if precision < 95% or recall < 90%** (SC-002/SC-007). Baseline: **P=1.000
  R=1.000 F1=1.000** on 315 cases; combined P=1.000 R=0.990. A weakened matcher trips the gate (shown
  by T045's tiny fixture: title-only → false positives → precision drop → gate fails).
- **API** (T050, `routers/evals.py`): `POST /evals/resolution/run?matcher=baseline|combined`,
  `GET /evals/resolution/latest`; golden path comes from the registered vertical. **UI** (T051,
  `app/evals/`): precision/recall/F1 tiles, gate badge, mismatched-case table, run button.
- **41 tests pass** (32 prior + 3 eval harness + 3 golden-gate guard + 3 evals API); ruff + black clean.
  **M2 done (eval side).** Rationale (hermetic embeddings + golden construction) logged in `decisions.md`.
  Next: Phase 6 (US4 — grounded AI agent, propose-only).

### 2026-10-23 (earlier · US2) — US2 implemented: decide → approve → act, safely (`002` Phase 4, T037–T044)

- Ran `/speckit-implement` for Phase 4 (US2), constitution-mandated tests first (T037 decision, T038 action seam).
- **Logic (read-only)**: `functions/registry.py` (T039) runs a registered `FunctionDef` with
  `repo.read_view()` — a `ReadOnlyStore` exposing no write method, so a function *cannot* mutate the
  store by the handle it holds. `apple_without_youtube` (T040) reasons over the fused ontology's
  `source_refs` (Apple present, YouTube absent) instead of the slice's bespoke Episode shape.
- **Action (the only writeback)**: engine `actions/port.py` + `audit.py` (T041) — `ActionExecutor`
  enforces the contract around a vertical-supplied `ActionHandler`: `preview`→mock logs the intent
  and makes no external call; `execute`→real refuses unless `approved=true` **and** `confirm_access`
  passes, computes an idempotency key from the ActionDef's declared fields, returns
  `skipped_idempotent` when that key already succeeded, and records **every** attempt via `AuditTrail`.
  `youtube_update_show_notes` (T042) appends a marker to an **owned** test video (refuses any other
  channel), idempotent on the marker, transport injected for testing.
- **API** (T043): `GET /functions`, `POST /functions/{key}/run` (no mutation), `GET /actions`,
  `POST /actions/{key}/preview`, `POST /actions/{key}/execute` (403 without approval, 409 if access
  unconfirmed), `GET /actions/attempts`. Handlers supplied by the vertical via `action_handlers(settings)`.
- **UI** (T044): `apps/web/app/ops/` — flagged episodes, a mock/real action console with an explicit
  approval checkbox (human-in-the-loop), and the audit-log timeline.
- **Deciding ≠ acting** holds end-to-end; writeback is safe/approved/idempotent/audited (SC-003).
- **32 tests pass** (21 prior + 2 decision + 5 action-seam + 4 actions API); ruff + black clean.
  Also hardened `find_attempt` (both repos) to prefer a settled attempt so a stale failure can't
  mask a prior success. **M1 is complete** (registries + safe-action port). Next: Phase 5 (US3 evals).
- **Known follow-up (noted, not US2 scope)**: both adapters' `map_*` emit `duration_seconds`, but the
  `episode` ObjectType and the matcher expect `duration_s` — so the duration signal/property is inert
  until the mapping key is aligned. Title + date still carry the match. Fix when wiring the live ingest.

### 2026-10-23 (earlier · US1) — US1 implemented: see the fused ontology (`002` Phase 3, T027–T036)

- Ran `/speckit-implement` for Phase 3 (US1 — the 🎯 MVP), tests-first per the constitution.
- **Resolution core (engine)**: `BaselineMatcher` (T029) — normalized-title + date + duration
  signals via rapidfuzz, `block`/`score`/`match` with greedy one-to-one (no fan-out), exposing
  `Signal`s + confidence and a best-rejected-candidate for singletons (Principle III); generic
  `conform` (T030) that is declaration-driven (fills scalar props by source-preference order and
  `<source>_ref` props per source, so no podcast specifics leak into the engine); the
  `IngestionPipeline` (T031) wiring adapter→stage→block→score→ResolutionDecision→upsert — **objects
  are only ever made from resolved staging** (Principle II).
- **API (apps/api)**: ingest router (T033 — `POST /ingest/run`, `GET /ingest/jobs/{id}`,
  `GET /access/check`) with an in-memory job store; ontology-explorer router (T034 —
  `/ontology/types`, `/ontology/types/{key}/instances` with `fused`/`source` filters,
  `/ontology/instances/{id}`, `/ontology/instances/{id}/resolution`, `/ontology/links`); the arq
  worker entrypoint (T032) reusing the same `execute_ingestion` callable; a store factory + the
  vertical's `source_targets` helper (keeps podcast ids out of the engine).
- **UI (apps/web)**: explorer (T035) — type list → instance list with fused badge + confidence →
  instance detail with source refs — and the resolution-inspection view (T036) showing the signal
  table, confidence, matcher, and best rejected candidate.
- **Tests (constitution-mandated)**: `test_baseline_matcher.py` (T027 — fuses same episode across
  sources, does not fuse different episodes, never pairs within one source, no fan-out) and
  `test_ingest_pipeline.py` (T028 — instances only from resolved staging; single-source stays
  single-source), plus `test_ontology_api.py` for the explorer + hermetic ingest endpoints.
- **Verification**: 21 tests pass; `ruff` + `black` clean. The explorer UI is coded but not yet run
  against a live ingest (deployed end-to-end is Phase 7, T062–T063). Next: Phase 4 (US2).

### 2026-10-23 (earliest) — M0 skeleton implemented (`002` Phases 1–2, T001–T026)

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
