---

description: "Task list for AI-Native Ontology Engine (Vertical #1: Podcast Ops)"
---

# Tasks: AI-Native Ontology Engine (Vertical #1: Podcast Ops)

**Input**: Design documents from `specs/002-ontology-engine/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (all present)

**Tests**: Included **only** where the constitution (v2.0.0) mandates them — entity-resolution and
read-only functions have automated tests (Principle VII), the action seam is exercised in mock mode
(Principle IV), and the AI layer has evals (Principle VI). Other areas are not blanket-TDD.

**Organization**: Grouped by user story (from spec.md) for independent implementation and testing.
Paths follow the monorepo in plan.md: `engine/`, `verticals/podcast/`, `apps/api/`, `apps/web/`,
`infra/`.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: parallelizable (different files, no dependency on an incomplete task)
- **[Story]**: US1–US4 (user-story phases only)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Monorepo layout, package scaffolds, local services, CI skeleton.

- [X] T001 Create monorepo structure per plan.md (`engine/`, `verticals/podcast/`, `apps/api/`, `apps/web/`, `infra/{docker,deploy,migrations}`, `.github/workflows/`)
- [X] T002 [P] Create `engine/pyproject.toml` (package `ontology_engine`, deps: pydantic v2, sqlalchemy 2, alembic, pgvector, httpx, rapidfuzz, anthropic; extras: `embeddings-voyage`, `embeddings-local`, `live`)
- [X] T003 [P] Create `verticals/podcast/pyproject.toml` (package `vertical_podcast`, depends on `ontology_engine`)
- [X] T004 [P] Create `apps/api/pyproject.toml` (FastAPI + Uvicorn; depends on `ontology_engine` + `vertical_podcast`)
- [X] T005 [P] Scaffold `apps/web/` Next.js + TypeScript + Tailwind app (explorer/dashboard/agent routes stubbed)
- [X] T006 [P] Author `infra/docker/docker-compose.yml` (services: postgres+pgvector, redis, langfuse) and base `Dockerfile` for the API
- [X] T007 [P] Carry forward and extend config/secrets: `.env.example` (YOUTUBE_API_KEY, youtube OAuth token path, ANTHROPIC_API_KEY, VOYAGE_API_KEY optional, DATABASE_URL, REDIS_URL, LANGFUSE_* , TARGET_YOUTUBE_SOURCE, TARGET_APPLE_SHOW, TEST_VIDEO_ID); confirm `.gitignore` covers `.env`, `secrets/`, `run/`
- [X] T008 [P] Configure `ruff` + `black` across all Python packages (line-length 100, carry slice config) and ESLint/Prettier for `apps/web`
- [X] T009 Create `.github/workflows/ci.yml` skeleton (lint + test jobs; eval-gate + deploy jobs added later in T049, T060–T061)

**Checkpoint**: Repos, services, and CI skeleton exist.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The engine core + vertical registration that every story needs. Migrates the proven
slice modules into their engine/vertical homes.

**⚠️ CRITICAL**: No user story work begins until this phase is complete.

- [X] T010 [P] Define ontology model in `engine/src/ontology_engine/ontology/types.py`: `ObjectType` (key unique, `properties`, `embeddable_fields`, `source_bindings`), `LinkType` (`key`, `from_type`, `to_type`, `cardinality` one|many)
- [X] T011 [P] Define `ObjectInstance` (`id`, `object_type_key`, `properties`, `source_refs` list — **≥1 entry; a fused instance has ≥2 from different sources**, `embedding` nullable) and `LinkInstance` in `engine/src/ontology_engine/ontology/instances.py`
- [X] T012 [P] Define `StagingRecord` (`id`, `source_key`, `object_type_key`, `external_id`, `raw_payload`, `fetched_at`, `status` staged|resolved|discarded) in `engine/src/ontology_engine/ingest/staging.py` (migrate from slice `ingest/staging.py`)
- [X] T013 [P] Define `ResolutionDecision` (`instance_id`, `members`, `signals[]` of `{name,value,weight,contribution}`, `confidence` 0–1, `matcher` baseline|similarity|combined, `decided_at`) in `engine/src/ontology_engine/resolve/decision.py`
- [X] T014 Define the `SourceAdapter` port (`read()->Iterable[StagingRecord]`, `capabilities()`, `confirm_access(capability)->AccessCheckResult`) in `engine/src/ontology_engine/ingest/adapter.py` (generalize slice gateways)
- [X] T015 Define the `Repository` port + `ReadOnlyStore` view in `engine/src/ontology_engine/store/repository.py` (stage/list_staging, upsert_instance/get/query, save_resolution/get_resolution, record_attempt/find_attempt/list_attempts, save_embedding/nearest, `read_view()`) — generalize slice `objects/repository.py`
- [X] T016 [P] Implement `JsonRepository` backend in `engine/src/ontology_engine/store/json_repo.py` (hermetic tests/offline; required for the CI eval gate)
- [X] T017 Implement `PostgresRepository` backend (SQLAlchemy 2 models + pgvector column) in `engine/src/ontology_engine/store/postgres_repo.py`
- [X] T018 Create Alembic setup + initial migration (objects, staging, resolution_decisions, action_attempts, embeddings, golden_cases, agent_interactions) in `infra/migrations/`
- [X] T019 [P] Implement the `EmbeddingProvider` port + `VoyageEmbeddings` + `LocalEmbeddings` (sentence-transformers) in `engine/src/ontology_engine/embeddings/` (provider chosen by config; local used in CI)
- [X] T020 [P] Implement the access-confirmation module (`AccessCheckResult`, per-adapter checks) in `engine/src/ontology_engine/access/check.py` (migrate slice `access_check.py`)
- [X] T021 Implement the `Vertical` registration mechanism in `engine/src/ontology_engine/ontology/registry.py` (register ObjectTypes, LinkTypes, SourceAdapters, FunctionDefs, ActionDefs, UI config, golden-set path) — **engine must discover a vertical only through this; no engine module imports a vertical module (Principle I)**
- [X] T022 [P] Register podcast object types + links in `verticals/podcast/src/vertical_podcast/objects/` (`Show`, `Episode` [title, description, published_at, duration_s, youtube_ref incl. public engagement counts, apple_ref, source_refs], `Guest`, `Clip`; links episode→show, episode→guest, episode→clip) (migrate slice `objects/episode.py`)
- [X] T023 [P] Implement the podcast `SourceAdapter`s in `verticals/podcast/src/vertical_podcast/sources/` (`youtube_adapter.py` read uploads + public engagement counts, write `videos.update`; `apple_adapter.py` read via iTunes lookup, no auth) (migrate slice `ingest/youtube_gateway.py`, `ingest/apple_gateway.py`)
- [X] T024 Create `verticals/podcast/src/vertical_podcast/registry.py` wiring the above into the engine registry
- [X] T025 Create the FastAPI app skeleton in `apps/api/src/app/main.py` that loads the engine, imports+applies the podcast `registry`, configures logging + error handling, and exposes `GET /health`
- [X] T026 [P] Centralized config loader (env → typed settings) in `engine/src/ontology_engine/config.py` (migrate/extend slice `config.py`)

**Checkpoint**: Engine core + podcast registration ready; app boots and health-checks.

---

## Phase 3: User Story 1 — See the fused ontology (Priority: P1) 🎯 MVP

**Goal**: Ingest the real show from both platforms, fuse the same episode into one `Episode`, and
browse the fused ontology (object types, instances, links, match confidence + signals) in the UI.

**Independent Test**: Run ingest; in the explorer, a two-platform episode is one fused `Episode`
showing both `source_refs`, its matched `signals`, and `confidence`; an Apple-only episode stays
single-source and is not falsely fused.

### Tests for User Story 1 (constitution-mandated: resolution)

- [ ] T027 [P] [US1] Unit test the baseline matcher in `engine/tests/test_baseline_matcher.py` (fuses mismatched-ID/slightly-different-title pairs; does **not** fuse near-duplicate-but-different episodes — edge case from spec)
- [ ] T028 [P] [US1] Integration test the ingest pipeline in `engine/tests/test_ingest_pipeline.py` (**assert an `ObjectInstance` is only created from resolved staging — never from a raw payload**; single-source stays single-source)

### Implementation for User Story 1

- [ ] T029 [US1] Implement the baseline `Matcher` (`block()` candidate generation + `score()` → signals+confidence via rapidfuzz on normalized title/date/duration) in `engine/src/ontology_engine/resolve/baseline.py` (migrate slice `resolve/matcher.py`)
- [ ] T030 [US1] Implement `conform` (staging → conformed `ObjectInstance` properties) in `engine/src/ontology_engine/resolve/conform.py` (migrate slice `resolve/conform.py`)
- [ ] T031 [US1] Implement the ingestion orchestrator (adapter → stage → block → score → `ResolutionDecision` → `upsert_instance` → generate+store embedding) in `engine/src/ontology_engine/ingest/pipeline.py`
- [ ] T032 [US1] Wire background ingestion: `arq` worker entrypoint in `apps/api/src/app/worker.py` calling the pipeline (same callable usable as a Cloud Run Job)
- [ ] T033 [US1] Implement ingestion endpoints in `apps/api/src/app/routers/ingest.py`: `POST /ingest/run` (enqueue, return job_id), `GET /ingest/jobs/{id}` (status + counts staged/fused/single_source), `GET /access/check`
- [ ] T034 [US1] Implement explorer endpoints in `apps/api/src/app/routers/ontology.py`: `GET /ontology/types`, `GET /ontology/types/{key}/instances` (paginated, `fused` filter), `GET /ontology/instances/{id}`, `GET /ontology/instances/{id}/resolution` (**signals[] + confidence + matcher + rejected best candidate**), `GET /ontology/links`
- [ ] T035 [P] [US1] Build the ontology explorer UI in `apps/web/app/explorer/` (type list, instance list with fused badge, instance detail with source_refs + linked instances)
- [ ] T036 [P] [US1] Build the resolution-inspection view in `apps/web/app/explorer/resolution/` (show matched signals + confidence for a fused Episode)

**Checkpoint**: US1 fully functional — fusion visible with platforms, signals, and confidence (SC-001).

---

## Phase 4: User Story 2 — Decide → approve → act, safely (Priority: P2)

**Goal**: A read-only function flags episodes; the operator approves; one safe, idempotent, audited
writeback runs (mock first, then real) to the owned test channel.

**Independent Test**: Function returns flagged episodes and mutates nothing; mock logs intent; real
writeback succeeds once; retry is `skipped_idempotent`; all attempts (mock + real) are in the audit.

### Tests for User Story 2 (constitution-mandated: functions + mock action seam)

- [ ] T037 [P] [US2] Unit test the decision function in `verticals/podcast/tests/test_decision.py` (correct flagging; **asserts it receives a read-only view and performs no writes**) (migrate slice `tests/unit/test_decision.py`)
- [ ] T038 [P] [US2] Test the action seam in `engine/tests/test_action_seam.py` (**mock mode makes no external call and logs intent; real mode requires `approved=true`; repeat with same idempotency key → `skipped_idempotent`; every attempt recorded**)

### Implementation for User Story 2

- [ ] T039 [US2] Implement the `FunctionDef` registry + read-only execution (functions get `ReadOnlyStore` only) in `engine/src/ontology_engine/functions/registry.py`
- [ ] T040 [P] [US2] Implement `apple_without_youtube` function in `verticals/podcast/src/vertical_podcast/functions/apple_without_youtube.py` (migrate slice `logic/decision.py`)
- [ ] T041 [US2] Implement the `ActionDef` + Action port (`preview`→mock ActionAttempt logging intent; `execute`→real, refuses unless `approved` and write-access confirmed; computes idempotency key; `skipped_idempotent` on repeat; persists every `ActionAttempt`) in `engine/src/ontology_engine/actions/port.py` + `audit.py` (migrate slice `action/writeback.py`, `action/audit_log.py`)
- [ ] T042 [P] [US2] Implement `youtube_update_show_notes` action (append marker via `videos.update`; target = owned test channel only; idempotent on marker) in `verticals/podcast/src/vertical_podcast/actions/update_show_notes.py`
- [ ] T043 [US2] Implement decision/action endpoints in `apps/api/src/app/routers/actions.py`: `GET /functions`, `POST /functions/{key}/run` (no mutation), `GET /actions`, `POST /actions/{key}/preview` (mock), `POST /actions/{key}/execute` (requires `{approved:true}`), `GET /actions/attempts`
- [ ] T044 [P] [US2] Build the ops dashboard + action console UI in `apps/web/app/ops/` (flagged episodes; mock/real toggle; approve+execute; audit-log timeline)

**Checkpoint**: US1 + US2 both work; deciding ≠ acting; writeback safe/idempotent/audited (SC-003).

---

## Phase 5: User Story 3 — Entity resolution, measured (Priority: P2)

**Goal**: Measure resolution (precision/recall/F1) against a labeled golden set, compare baseline vs
similarity matcher, and gate CI against regression.

**Independent Test**: The ER eval reports precision/recall + mismatched pairs on the golden set;
weakening a matcher rule makes the CI gate fail.

### Tests for User Story 3 (constitution-mandated: resolution evaluated)

- [ ] T045 [P] [US3] Test the eval harness in `engine/tests/test_resolution_eval.py` (computes correct precision/recall/F1 on a tiny fixture; **detects a deliberately weakened matcher as a regression**)

### Implementation for User Story 3

- [ ] T046 [US3] Seed the golden set in `verticals/podcast/evals/golden/` from the slice's 199 real matched pairs **plus curated hard negatives (near-duplicate titles/dates)**; add a `GoldenCase` loader (`kind` match|non_match)
- [ ] T047 [US3] Implement the similarity `Matcher` (embedding cosine via pgvector `nearest`) in `engine/src/ontology_engine/resolve/similarity.py`, and the `CombinedMatcher` merging baseline+similarity into one `ResolutionDecision` — **baseline MUST remain runnable alone for comparison (Principle III)**
- [ ] T048 [US3] Implement the ER eval harness (precision/recall/F1, mismatch list, threshold, JSON report; runs hermetic on JsonRepository + LocalEmbeddings) in `engine/src/ontology_engine/evals/resolution.py`
- [ ] T049 [US3] Add the CI eval gate job to `.github/workflows/ci.yml` (runs T048 hermetically; **fails the build if precision < 95% or recall < 90%** per SC-002/SC-007)
- [ ] T050 [P] [US3] Implement eval endpoints in `apps/api/src/app/routers/evals.py`: `POST /evals/resolution/run`, `GET /evals/resolution/latest`
- [ ] T051 [P] [US3] Build the eval dashboard UI in `apps/web/app/evals/` (precision/recall/F1 over time; list of mismatched cases)

**Checkpoint**: Resolution is measurable and regression-gated (SC-002, SC-007).

---

## Phase 6: User Story 4 — Grounded AI agent, propose-only (Priority: P3)

**Goal**: An agent answers show questions grounded in objects (with citations) and *proposes*
actions (never executes); the operator approves to act; AI is traced and evaluated.

**Independent Test**: A grounded question returns an answer citing real Episode ids; a proposed
action changes nothing until approved; an ungrounded question yields a "no grounded data" answer; a
Langfuse trace_id is recorded.

### Tests for User Story 4 (constitution-mandated: AI evals)

- [ ] T052 [P] [US4] AI eval set + runner in `engine/tests/test_agent_evals.py` and `engine/src/ontology_engine/evals/agent.py`: deterministic checks (**every citation resolves to a real ObjectInstance; proposed-action inputs are schema- and policy-valid**) + grounded vs ungrounded cases; **LLM-as-judge on Claude Haiku 5.5 (`claude-haiku-5-5`)** for faithfulness/relevance

### Implementation for User Story 4

- [ ] T053 [US4] Implement grounded retrieval tools (`search_objects`, `get_object`, `traverse`, `run_function`) in `engine/src/ontology_engine/ai/tools.py` (side-effect-free; return real object ids)
- [ ] T054 [US4] Implement the agent on **Claude Opus 5.5 (`claude-opus-5-5`)** via the SDK Tool Runner (`client.beta.messages.tool_runner`) with the grounding context under `cache_control: ephemeral`, adaptive thinking on, in `engine/src/ontology_engine/ai/agent.py`; returns a `GroundedAnswer` (`answer_text`, `citations[]`, `proposed_actions[]`, `trace_id`)
- [ ] T055 [US4] Implement the `propose_action` tool (validates input against the `ActionDef` + owned-target policy, stores a proposal + mock preview; **MUST NOT call the Action port `execute`**) in `engine/src/ontology_engine/ai/propose.py`
- [ ] T056 [P] [US4] Implement Langfuse tracing adapter behind the engine `trace()` seam in `engine/src/ontology_engine/ai/tracing.py`
- [ ] T057 [US4] Implement agent endpoints in `apps/api/src/app/routers/agent.py`: `POST /agent/ask` (streamed GroundedAnswer), `POST /agent/proposals/{id}/approve` (routes through the human-approved `/actions/{key}/execute` path)
- [ ] T058 [P] [US4] Build the agent chat UI in `apps/web/app/agent/` (stream answer + show citations as links to objects; render proposed actions with an explicit approve button)

**Checkpoint**: Grounded, traced, propose-only agent; zero autonomous external changes (SC-004).

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Deploy, prove the seam, validate end-to-end on the real show, document.

- [ ] T059 [P] Seam check: automated test/CI step asserting **no `engine/` module imports `verticals/`** and podcast types appear only via `verticals/podcast/registry.py` (SC-005) in `engine/tests/test_engine_vertical_seam.py`
- [ ] T060 Author deploy config in `infra/deploy/` (Cloud Run service for the API, Cloud Run Job + Cloud Scheduler for ingestion, Neon/Cloud SQL Postgres w/ pgvector, Vercel for `apps/web`, GCP Secret Manager for secrets)
- [ ] T061 Extend `.github/workflows/` with build+push image and deploy-to-Cloud-Run jobs (gated behind lint + test + eval gate); confirm Vercel auto-deploy for `apps/web`
- [ ] T062 Run the M0 access gate live (`GET /access/check`) against the real show config and confirm 3/3 (YouTube read, Apple read, YouTube write scope)
- [ ] T063 Execute `quickstart.md` Scenarios 1–4 against the **deployed** environment on the real show (Huberman Lab) — the full spine end-to-end (SC-006); capture the audit trail
- [ ] T064 [P] Write `README.md` (architecture: engine vs vertical, run/deploy, the data→logic→action→AI story) and a short architecture diagram
- [ ] T065 [P] Update `progress.md` (mark M0–M4 status as built) and add any deviations to `decisions.md`
- [ ] T066 [P] Security pass: confirm no secrets committed, prod secrets in Secret Manager, owned-target-only enforced on actions, agent cannot execute un-approved actions

---

## Dependencies & Execution Order

### Phase dependencies
- **Setup (P1)**: no dependencies.
- **Foundational (P2)**: depends on Setup — **blocks all user stories**.
- **US1 (P3)** → **US2 (P4)** → **US3 (P5)** → **US4 (P6)**: each depends only on Foundational and can be demoed independently; natural order is priority order (US2 uses US1's objects; US3 measures US1's resolution; US4 grounds on US1 objects + US2 actions).
- **Polish (P7)**: depends on the stories you choose to ship (T063 needs US1+US2 at minimum).

### Within each story
- Constitution-mandated tests (T027/T028, T037/T038, T045, T052) are written to fail first, then implementation.
- Models/ports before services; services before endpoints; endpoints before UI.

### Parallel opportunities
- Setup: T002–T008 are all [P].
- Foundational: T010–T013, T016, T019, T020 are [P]; T022/T023 are [P] (vertical) once the ports (T014) exist.
- Within a story, [P] tasks touch different files (e.g. US1 UI T035/T036 parallel to each other; API vs UI generally parallel once endpoints' shapes are fixed by contracts/).
- Across stories: after Foundational, US1–US4 can be staffed in parallel, honoring the integration notes above.

---

## Parallel Example: User Story 1

```bash
# Constitution-mandated tests first (parallel):
Task: "Unit test the baseline matcher in engine/tests/test_baseline_matcher.py"
Task: "Integration test the ingest pipeline in engine/tests/test_ingest_pipeline.py"

# UI surfaces in parallel once endpoints are defined:
Task: "Build the ontology explorer UI in apps/web/app/explorer/"
Task: "Build the resolution-inspection view in apps/web/app/explorer/resolution/"
```

---

## Implementation Strategy

### MVP first (US1 only)
1. Phase 1 Setup → 2. Phase 2 Foundational → 3. Phase 3 US1 → 4. **STOP & validate** SC-001 in the explorer → 5. deploy/demo. This is M0+M1 made visible.

### Incremental delivery
- + US2 → safe action spine (SC-003) → demo
- + US3 → measured resolution + CI gate (SC-002/SC-007) → demo
- + US4 → grounded agent (SC-004) → demo
- Polish → deploy on real show (SC-006), prove the seam (SC-005)

### Note on earned generality
Vertical #2 (M5) is **not** in this task list by design. Only build it in a later cycle; it is the
generality proof, and nothing here should add engine abstractions US1–US4 do not use (Principle I).

---

## Notes
- [P] = different files, no dependency on an incomplete task.
- Many engine tasks are *migrations* of proven slice modules (noted inline) — generalize, don't rewrite.
- Keep the engine/vertical seam clean (T059 guards it); commit after each task or logical group.
- The resolution eval (T048) and its CI gate (T049) must stay hermetic — no live external calls.
