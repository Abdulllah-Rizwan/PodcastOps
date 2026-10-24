# Ontology Engine — proven by verticals

A reusable, **AI-native ontology engine** that implements the **data → logic → action** pattern:
objects fused from systems we don't own, read-only functions that *decide*, and safe actions that
*change the world* — with an AI agent grounded in the ontology on top. The engine is domain-agnostic;
it is proven by building **verticals** on it. **Podcast operations is vertical #1** — the live demo
that fuses one real show across YouTube and Apple Podcasts, flags episodes, and writes back safely to
a throwaway test channel.

> Generality is **earned, never asserted**: one vertical is a demo; a *second, different* vertical on
> the same engine with no engine rewrite (milestone M5) is the proof. The engine must not grow
> abstractions no current vertical uses.

Governance lives in [`.specify/memory/constitution.md`](.specify/memory/constitution.md) (v2.0.0) and
the brief [`CLAUDE.md`](CLAUDE.md). The full spec/plan/tasks for this build are under
[`specs/002-ontology-engine/`](specs/002-ontology-engine/). Where this README and the constitution
differ, the constitution governs.

## The pattern: data → logic → action → AI

```
                            ┌──────────────────────────────────────────────────────┐
                            │                    ONTOLOGY ENGINE                     │
                            │                  (domain-agnostic core)                │
  YouTube ─┐                │                                                        │
           │   read()       │   ┌─────────┐   resolve + conform   ┌──────────────┐   │
           ├──────────────► │   │ STAGING │ ────────────────────► │   OBJECTS    │   │
  Apple  ──┘  SourceAdapter │   │ (raw)   │   entity resolution   │ + typed LINKS│   │
                            │   └─────────┘   (baseline/vector)   └──────┬───────┘   │
                            │       DATA ─────────────────────────────►  │           │
                            │                                            ▼           │
                            │   LOGIC = FUNCTIONS (read-only; ReadOnlyStore)         │
                            │        "what should we do?" — decide, change nothing   │
                            │                                            │           │
                            │                                            ▼           │
                            │   ACTION (the only writer): preview→mock, execute→real │
                            │        safe · idempotent · audited · owned-target-only │
                            │                                            │           │
                            │   AI AGENT (Opus 5.5): reads via objects/functions,    │
                            │        *proposes* actions with citations — never acts  │
                            │        human approves ───────────────────►┘           │
                            └───────────────────────────────┬────────────────────────┘
                                                            │ writeback (YouTube videos.update)
                                                            ▼
                                              owned throwaway test channel
```

- **Data → Objects.** Raw platform data lands in a **staging area first**, is **resolved and
  conformed**, and only then becomes an **object**. The object is the clean, fused result, never the
  raw inlet. **Entity resolution is the hard core**: matching the same real episode across YouTube and
  Apple (mismatched IDs, titles, schemas) into one `Episode`. It is measured (precision/recall) against
  a labeled golden set and gated in CI.
- **Logic = Functions.** Read-only. They receive a `ReadOnlyStore` (no write method by the handle they
  hold, not by convention) and decide. They change nothing.
- **Action.** The only component that mutates external state. `preview` logs intent and makes no call;
  `execute` refuses unless `approved=true` **and** write-access is confirmed, computes an idempotency
  key, returns `skipped_idempotent` on repeat, and records every attempt in an audit trail.
- **AI.** The agent reads the world only through objects/links/functions and **proposes** validated
  actions with citations to real object ids; a human approves before anything executes. AI is traced
  and covered by evals.

## Engine vs vertical (the hard seam)

The engine owns the generic machinery; a vertical is a plugin that declares its specifics and is
discovered **only** through the registry — no engine module imports a vertical (guarded by
`engine/tests/test_engine_vertical_seam.py`).

```
engine/            ontology_engine — the reusable core (domain-agnostic)
  ontology/          ObjectType/LinkType, ObjectInstance/LinkInstance, the Vertical registry
  ingest/            SourceAdapter port, StagingRecord, the ingestion pipeline
  resolve/           baseline matcher, similarity (vector) matcher, combined, conform, decisions
  functions/         read-only FunctionDef registry (hands out ReadOnlyStore only)
  actions/           the safe Action port + audit trail
  ai/                grounded tools, the agent (Opus 5.5 Tool Runner), propose_action, tracing seam
  evals/             resolution eval harness + CI gate, agent evals
  store/             Repository port; JsonRepository (hermetic) + PostgresRepository (pgvector)
  embeddings/        EmbeddingProvider port; Voyage (hosted) / Local / Hashing (hermetic) providers

verticals/podcast/  vertical_podcast — vertical #1 (the only place podcast specifics live)
  objects/           Show, Episode, Guest, Clip + links
  sources/           YouTube adapter (read + videos.update write), Apple adapter (iTunes lookup)
  functions/         apple_without_youtube
  actions/           youtube_update_show_notes (owned test channel only, idempotent on a marker)
  evals/golden/      199 real matched pairs + 116 curated hard negatives
  registry.py        wires all of the above into the engine — the engine's only discovery path

apps/api/           FastAPI over the core (thin: wiring + HTTP, no domain logic)
apps/web/           Next.js UI — explorer, ops dashboard, eval dashboard, agent chat
infra/              docker-compose (postgres+pgvector, redis, langfuse), API Dockerfile, migrations, deploy
.github/workflows/  CI: lint, test, and the hermetic entity-resolution eval gate
```

## Run it locally

All tests and the mock spine are **hermetic** — no credentials, no network, no services. The default
store is JSON; set `DATABASE_URL` to use Postgres + pgvector.

```bash
# 1) Install the three Python packages (editable)
pip install -e "./engine[dev,embeddings-local]"
pip install -e "./verticals/podcast[dev]"
pip install -e "./apps/api[dev]"

# 2) Tests (bare `pytest` under-collects — name the three roots)
#    PowerShell uses ';' as the PYTHONPATH separator (shown); bash uses ':'.
$env:PYTHONPATH="engine/src;verticals/podcast/src;apps/api/src"
pytest engine/tests verticals/podcast/tests apps/api/tests     # -> 61 passed

# 3) Lint / format
ruff check engine verticals apps/api
black --check engine verticals apps/api

# 4) Entity-resolution eval gate (hermetic; fails if precision < 95% or recall < 90%)
python -m ontology_engine.evals.run_gate verticals/podcast/evals/golden baseline

# 5) API (http://localhost:8000/health shows the registered ontology)
uvicorn app.main:app --reload --app-dir apps/api/src

# 6) Optional backing services (Postgres+pgvector, Redis, Langfuse)
docker compose -f infra/docker/docker-compose.yml up -d

# 7) Background ingestion worker (needs Redis)
arq app.worker.WorkerSettings        # run from apps/api/src on PYTHONPATH

# 8) Web UI
cd apps/web && npm install && npm run dev        # http://localhost:3000
```

Copy `.env.example` to `.env` (untracked) and fill in only what a given run needs. The mock spine and
the whole test suite run with everything blank. Live reads need `YOUTUBE_API_KEY` (Apple needs none);
the real writeback needs a YouTube OAuth token for an **owned** channel; the agent needs
`ANTHROPIC_API_KEY` (without it `/agent/ask` returns a graceful 503).

## Deploy (default target: GCP Cloud Run + Vercel + Neon)

- **API** → Cloud Run service (container from `infra/docker/Dockerfile.api`).
- **Ingestion worker** → Cloud Run Job triggered by Cloud Scheduler (same `execute_ingestion` callable
  as the API).
- **Database** → Neon Postgres with `pgvector` (via `DATABASE_URL`); schema from `infra/migrations`.
- **Web** → Vercel (`apps/web`).
- **Secrets** → GCP Secret Manager — never committed `.env` files.
- **CI/CD** → `.github/workflows/ci.yml` runs lint + tests + the eval gate; build/push + deploy jobs are
  gated behind all three.

Deploy config lives in `infra/deploy/`. The first live end-to-end run on the real show (the full spine,
with a captured audit trail) is milestone M4 and is tracked in `progress.md`.

## Status

Milestones **M0–M3 complete** (full-stack skeleton; generalized ontology core; measured, CI-gated
entity resolution; grounded propose-only AI agent). **M4** (harden & deploy for real) is in progress.
**M5** (a second vertical, the generality proof) is deliberately not yet built. See `progress.md` for
the live status and `decisions.md` for every deviation from plan.
