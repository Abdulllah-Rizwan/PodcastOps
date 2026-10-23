# Implementation Plan: AI-Native Ontology Engine (Vertical #1: Podcast Ops)

**Branch**: `002-ontology-engine` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-ontology-engine/spec.md`

## Summary

Build a reusable, domain-agnostic **ontology engine** (objects, typed links, read-only functions,
validated actions, grounded-and-evaluated AI) and prove it with **vertical #1 = podcast ops**. The
engine is the product; the vertical is a plugin. The approach reuses and generalizes the proven
Python core from the completed slice (ingest gateways, staging, matcher, `Episode` objects, decision
rule, writeback seam + audit log) rather than rewriting it: the slice's generic pieces become engine
packages, and its podcast-specific pieces move into a podcast vertical plugin. We add a FastAPI API,
Postgres + pgvector storage, a background ingestion worker, a Next.js web UI (ontology explorer +
ops dashboard + agent chat), an eval + tracing harness, and cloud deployment with a CI eval gate.
Delivery is milestone-phased (M0 skeleton → M1 generalized core → M2 vector ER + evals → M3 AI agent
→ M4 harden/deploy); **vertical #2 (M5) is explicitly out of scope** to honor earned-generality.

## Technical Context

**Language/Version**: Python 3.11+ (backend, engine, vertical, evals); TypeScript 5.x (frontend).

**Primary Dependencies**:
- Backend/engine: FastAPI + Uvicorn, Pydantic v2, SQLAlchemy 2.x + Alembic, `pgvector`, httpx,
  `rapidfuzz` (deterministic baseline matcher, already in use).
- AI: `anthropic` SDK — agent + generation on **Claude Opus 5.5** (`claude-opus-5-5`), LLM-as-judge
  in evals on **Claude Haiku 5.5** (`claude-haiku-5-5`); agent loop via the SDK **Tool Runner**
  (`client.beta.messages.tool_runner`); **prompt caching** on the ontology grounding context.
- Embeddings: provider behind a port (Anthropic offers none) — default **Voyage AI**, offline/dev
  fallback **sentence-transformers** (local); vectors stored in **pgvector**.
- Tracing/observability: **Langfuse** (LLM traces + online evals); OpenTelemetry as the alternative.
- Worker: `arq` + Redis (local/dev); Cloud Run Job + Cloud Scheduler in cloud.
- Frontend: Next.js (React) + Tailwind; data-fetching against the API.

**Storage**: PostgreSQL 16 + `pgvector` extension (objects, staging, resolution decisions, audit,
embeddings). A `Repository` seam retains a JSON-file backend for hermetic tests and offline runs.

**Testing**: `pytest` (engine/vertical/evals; resolution + functions + mock-action seam + AI evals);
Vitest + Playwright (frontend, light). `ruff` + `black` (already configured).

**Target Platform**: Linux containers. Backend → **GCP Cloud Run**; Postgres → managed
(**Neon** default, or Cloud SQL for an all-GCP footprint); frontend → **Vercel**; secrets → **GCP
Secret Manager** (prod), `.env` (local). CI/CD → GitHub Actions.

**Project Type**: Web application (backend API + frontend) built on a reusable engine library, with
a background worker and an eval harness. Monorepo.

**Performance Goals**: Not latency-critical. Targets: full ingest+fuse of vertical #1's real show
completes as a background job in minutes; explorer reads are interactive (< 1s typical page);
resolution eval runs on the golden set in seconds; agent answers stream.

**Constraints**: Public-data reads only for shows we don't own; actions only to owned test channel;
AI never mutates autonomously (human-in-the-loop); no secrets in the repo; eval gate must be able to
run hermetically in CI (no live external calls required for the resolution eval).

**Scale/Scope**: One real show (~500–1000 episodes per platform), one operator, one write target.
Engine built vertical-shaped; no multi-tenant, no second vertical in this feature.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Checked against
constitution **v2.0.0**.

| Principle | Gate | Status |
|-----------|------|--------|
| I. Engine First, Proven by Verticals | Engine code contains no vertical-specific types/sources/functions/actions; no abstraction unused by vertical #1; vertical #2 not built | ✅ Enforced by `engine/` vs `verticals/podcast/` split; M5 out of scope |
| II. Ontology stage separation | raw → staging → resolve → object; functions read-only; only actions mutate | ✅ Pipeline + registries in data-model; functions have no write path |
| III. Entity resolution hard core | explicit, inspectable, measurable; baseline retained alongside similarity; signals + confidence exposed | ✅ Dual matcher + ResolutionDecision records + ER eval (US3) |
| IV. Safe, logged, mock-first actions | mock-first, safe, idempotent, audited, owned-target-only; AI-proposed actions need human approval | ✅ Action port + audit + idempotency key + approval gate (contracts) |
| V. Confirm access before modeling | each source's read/write verified before modeling | ✅ `access_check` generalized per source adapter (M0 gate) |
| VI. AI grounded + evaluated | AI reads via ontology, writes only via actions; evals + tracing; CI gate | ✅ Agent tools = functions + propose_action; Langfuse traces; eval CI gate |
| VII. Code quality, full stack | seams/DI mockable; tests for resolution+functions; mock-action tests; AI evals; config externalized; no secrets | ✅ Repository/port seams; pytest + frontend tests; Secret Manager |

**Result: PASS (no violations).** The added full-stack surface (frontend, API, worker, cloud) is
in scope under constitution v2.0.0 and does not constitute scope creep. Complexity Tracking is
therefore empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-ontology-engine/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API + engine ports)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

Monorepo. The existing `src/podcast_ops/` is migrated: its generic pieces become the `engine/`
package; its podcast-specific pieces become the `verticals/podcast/` plugin.

```text
engine/                              # reusable, domain-agnostic core (Python package: ontology_engine)
├── src/ontology_engine/
│   ├── ontology/                    # object type + link + instance model; the registry
│   ├── ingest/                      # SourceAdapter port; staging store  (from slice: ingest/staging)
│   ├── resolve/                     # baseline matcher + similarity matcher; conform; ResolutionDecision
│   ├── functions/                   # read-only function registry
│   ├── actions/                     # Action port; validation; idempotency; mock + audit  (from slice: action/)
│   ├── ai/                          # grounded retrieval; agent (Tool Runner); tracing
│   ├── store/                       # Repository: Postgres+pgvector backend + JSON backend  (from slice: objects/repository)
│   ├── embeddings/                  # EmbeddingProvider port: Voyage + local fallback
│   ├── evals/                       # ER metrics; LLM-judge; golden-set loaders; thresholds
│   └── access/                      # access-confirmation per adapter  (from slice: access_check)
└── tests/
verticals/podcast/                   # vertical #1 plugin (Python package: vertical_podcast)
├── src/vertical_podcast/
│   ├── objects/                     # Show, Episode, Guest, Clip registration  (from slice: objects/episode)
│   ├── sources/                     # youtube + apple adapters  (from slice: ingest/*_gateway)
│   ├── functions/                   # e.g. apple_without_youtube  (from slice: logic/decision)
│   ├── actions/                     # YouTube show-notes writeback  (from slice: action/writeback)
│   └── registry.py                  # registers the above with the engine
├── tests/
└── evals/golden/                    # seeded golden set (199 real matched pairs from the slice)
apps/
├── api/                             # FastAPI app: wires engine + registered verticals; REST endpoints
│   └── tests/
└── web/                             # Next.js frontend: ontology explorer, ops dashboard, agent chat
    └── tests/
infra/
├── docker/                          # Dockerfiles + docker-compose (api, worker, postgres+pgvector, redis)
├── deploy/                          # Cloud Run / Vercel / Neon|Cloud SQL config + notes
└── migrations/                      # Alembic migrations
.github/workflows/                   # CI: lint, test, eval gate, build+push image, deploy
```

**Structure Decision**: Monorepo with a hard **`engine/` ↔ `verticals/podcast/`** package boundary
(Principle I/VII seam), an `apps/` layer for the thin API and the frontend, and `infra/` for
containers, deploy, and CI. The slice's proven modules are migrated into these packages (mapping
noted inline above) rather than rewritten. The `apps/api` is deliberately thin — it wires the engine
to the registered vertical and exposes HTTP; no domain logic lives there.

## Complexity Tracking

> No constitution violations — section intentionally empty.
