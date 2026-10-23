# Phase 0 Research — AI-Native Ontology Engine

**Feature**: `002-ontology-engine` | **Date**: 2026-10-23

All Technical Context items are resolved below (no remaining NEEDS CLARIFICATION). Each decision
notes rationale and the alternatives considered. Decisions marked *(carried forward)* reuse the
proven slice; the rest are new choices for the full-stack build.

---

## 1. Reuse vs rewrite the slice *(carried forward)*

- **Decision**: Reuse and *generalize* the existing `src/podcast_ops/` code. Generic modules
  (staging, matcher, repository, action seam + audit, access_check) migrate into `engine/`;
  podcast-specific modules (youtube/apple gateways, `Episode`, decision rule, writeback) migrate
  into `verticals/podcast/`.
- **Rationale**: The slice already ran end-to-end on live data; its seams (ports for gateways,
  repository, writeback) are exactly the inversion the engine needs. Rewriting would discard proven,
  tested code and violate ship-not-learn.
- **Alternatives**: Greenfield rewrite (rejected — wasteful, loses tests); keep slice as-is and wrap
  (rejected — leaves podcast specifics tangled in would-be engine code, breaking Principle I seam).

## 2. Backend framework — FastAPI

- **Decision**: FastAPI + Uvicorn, Pydantic v2 (already a dependency).
- **Rationale**: Async, first-class Pydantic models (reuse existing object schemas as API DTOs),
  OpenAPI for free (feeds the contracts and the frontend client), minimal boilerplate. Python keeps
  the engine and API in one language, so the engine is imported directly, not re-served.
- **Alternatives**: Flask/Django (heavier or sync-first); a separate Node backend (rejected — splits
  the engine from its API across languages).

## 3. Storage — PostgreSQL 16 + pgvector; Repository seam keeps JSON

- **Decision**: Postgres 16 with the `pgvector` extension as the single store for objects, staging,
  resolution decisions, audit records, and embeddings. SQLAlchemy 2.x + Alembic migrations. The
  existing `Repository` abstraction keeps a JSON-file backend for hermetic tests and offline runs.
- **Rationale**: One database for relational + vector means the fewest moving parts (Principle VII
  YAGNI); pgvector is sufficient at this scale (~1k rows). Keeping the JSON backend lets the
  resolution eval and unit tests run with no database or network (required for the CI eval gate).
- **Alternatives**: Dedicated vector DB (Qdrant/Weaviate/Pinecone) — rejected for now as an extra
  service with no benefit at this scale; revisit only if a future vertical needs it (earned
  generality). SQLite + vector extension — rejected; Postgres is the deploy target anyway.

## 4. Embeddings — provider port; Voyage default, local fallback

- **Decision**: An `EmbeddingProvider` port with two implementations: **Voyage AI** (default, hosted)
  and **sentence-transformers** (local, offline/dev + CI). Embeddings are stored in pgvector.
- **Rationale**: Anthropic does not offer an embeddings endpoint, so embeddings are a separate
  dependency — isolating it behind a port (Principle VII dependency inversion) keeps the engine
  provider-agnostic and lets evals/tests run locally with no API key or cost. Voyage is a strong,
  Anthropic-recommended default for quality; the local model keeps CI hermetic and free.
- **Alternatives**: OpenAI `text-embedding-3` (viable; another vendor key — fine as a third adapter
  later); embeddings-only-local (rejected as default — lower quality for the ER upgrade). The
  baseline deterministic matcher (rapidfuzz) is always retained regardless, per Principle III.

## 5. Entity resolution — dual matcher (baseline + similarity)

- **Decision**: Keep the deterministic baseline matcher (normalized title/date/duration via
  rapidfuzz, from the slice) and add a similarity matcher (embedding cosine over title+description,
  pgvector nearest-neighbor) combined into a scored `ResolutionDecision` that records contributing
  signals + confidence. A blocking step (candidate generation) precedes scoring.
- **Rationale**: Principle III demands an inspectable, measurable matcher with a baseline to evaluate
  the upgrade against. Recording per-signal contributions makes matches explainable in the explorer
  (SC-001) and gradeable in evals (SC-002).
- **Alternatives**: Pure-LLM matching (rejected — opaque, costly, unmeasurable baseline); exact-ID
  matching (rejected — the slice already showed IDs mismatch across platforms).

## 6. AI layer — Claude via Tool Runner, grounded + human-in-the-loop

- **Decision**: Use the `anthropic` SDK. The agent runs on **Claude Opus 5.5** (`claude-opus-5-5`)
  via the SDK **Tool Runner** (`client.beta.messages.tool_runner`). The agent's tools are
  (a) read-only engine **functions** / grounded retrieval over objects+links+embeddings, and
  (b) a `propose_action` tool that returns a *proposal* only — it never executes. Execution goes
  through the normal Action port after **human approval**. Generation (show-notes/clip drafts) also
  uses Opus 5.5. **Prompt caching** (`cache_control: ephemeral`) wraps the ontology grounding
  context to cut cost on multi-turn chat. Adaptive thinking is left on.
- **Rationale**: Principle VI — AI reads via the ontology and writes only via validated, approved
  actions. Tool Runner gives the agent loop with per-turn hooks for approval gating without
  hand-writing the loop. Opus 5.5 is the current default model; caching the (stable) grounding
  context is the right prefix-cache shape.
- **Alternatives**: LangChain/LangGraph or a heavy agent framework (rejected — over-abstraction for
  one agent; direct SDK is more legible and a better showcase of the primitives). Letting the agent
  call the Action port directly (rejected — violates human-in-the-loop, Principle IV/VI). A cheaper
  agent model (Sonnet 5.5) is a later cost lever, not the default.

## 7. Evals — in-repo harness, CI gate, LLM-judge on Haiku

- **Decision**: An in-repo eval harness. (a) **Entity-resolution eval**: precision/recall/F1 against
  the labeled golden set (seeded from the slice's 199 real matched pairs + hard negatives), runs
  hermetically (JSON backend, local embeddings), emits a JSON report, and **gates CI** on a
  threshold (SC-002/SC-007). (b) **AI eval**: deterministic checks (answer cites real object ids;
  proposed actions are schema-valid and policy-valid) plus **LLM-as-judge on Claude Haiku 5.5**
  (`claude-haiku-5-5`) for answer faithfulness/relevance. Online traces via Langfuse.
- **Rationale**: Principle VI makes evals mandatory and CI-gating. Haiku is the cheap-judge model.
  Keeping the ER eval hermetic means CI needs no secrets or live calls.
- **Alternatives**: promptfoo/Braintrust (viable external tools — deferred; an in-repo harness has
  zero vendor lock-in and is easy to show). Human-only eval (rejected — not repeatable/CI-gating).

## 8. Tracing/observability — Langfuse

- **Decision**: Langfuse for LLM tracing + online evals (self-host via compose locally, Langfuse
  Cloud in deploy). OpenTelemetry via the SDK is the documented alternative.
- **Rationale**: Purpose-built for LLM traces, prompt/version tracking, and online scoring — the
  showcase-relevant observability story. Self-hostable keeps cost and lock-in low.
- **Alternatives**: Raw OTel to a generic backend (more setup, less LLM-aware); LangSmith (vendor
  lock, paid). Either can replace Langfuse behind the same tracing seam.

## 9. Background worker — arq + Redis (local), Cloud Run Job (cloud)

- **Decision**: Ingestion is a plain callable entrypoint. Locally it runs via CLI or an `arq` worker
  on Redis; in cloud it runs as a **Cloud Run Job** triggered by **Cloud Scheduler**. Same code path
  both ways.
- **Rationale**: Ingestion is periodic and I/O-bound, not request-path. Cloud Run scales to zero, so
  an always-on Celery worker is a poor fit; a scheduled Job matches the workload and the deploy
  target. arq is lightweight and async-native for local/dev.
- **Alternatives**: Celery (heavier, always-on); FastAPI BackgroundTasks only (rejected — dies with
  the request, no retry/schedule); Cloud Tasks queue (viable later for on-demand ingest).

## 10. Frontend — Next.js on Vercel

- **Decision**: Next.js (React) + TypeScript + Tailwind, deployed to Vercel, consuming the FastAPI
  OpenAPI. Three surfaces: ontology explorer, podcast ops dashboard, agent chat.
- **Rationale**: Mature, fast to build, first-class Vercel deploy, pairs cleanly with a separate
  Cloud Run API. Explorer is the showcase artifact (makes resolution inspectable — Principle III).
- **Alternatives**: SvelteKit/Remix (fine, less ecosystem familiarity); server-rendered templates
  from FastAPI (rejected — weaker UX for an interactive explorer/chat).

## 11. Cloud + CI/CD — Cloud Run + Vercel + Neon + GitHub Actions

- **Decision**: Backend container → **GCP Cloud Run**; Postgres → **Neon** (serverless, pgvector;
  Cloud SQL as the all-GCP alternative); frontend → **Vercel**; secrets → **GCP Secret Manager**
  (prod). CI/CD → **GitHub Actions**: lint → test → **eval gate** → build+push image → deploy Cloud
  Run; Vercel auto-deploys the frontend.
- **Rationale**: Serverless, scales to zero, cheap for a one-operator showcase; the eval gate in CI
  satisfies SC-007. Neon's free tier + pgvector avoids standing up a managed DB cluster.
- **Alternatives**: AWS ECS/Fargate + RDS (heavier "enterprise" signal, more ops — a later option);
  single-PaaS (Railway/Render/Fly) (fastest, least cloud depth). YouTube OAuth token handling stays
  as the slice had it (user-run `auth` flow), with the token in Secret Manager in cloud.

---

## M0 access-confirmation checklist (Principle V gate, per source)

Carried from the slice and generalized to the adapter interface. Before modeling objects/actions
against a source, confirm:

- **YouTube read**: API key valid; channel/uploads playlist reachable; public engagement counts
  returned; quota headroom for ~1k videos.
- **Apple Podcasts read**: iTunes lookup returns full episode list for the show id (no auth).
- **YouTube write**: OAuth token with `youtube.force-ssl` scope present; `videos.update` permitted on
  the owned test video; write is to an owned channel only.
- **Embedding provider**: Voyage key present (or local model available) — not required for the
  hermetic ER eval.
- **Anthropic**: credential resolvable (`ANTHROPIC_API_KEY` or `ant auth` profile) for agent/eval.

Access results are surfaced by the engine's `access` check (reused `check-access` behavior) and must
pass before the vertical is run live.
