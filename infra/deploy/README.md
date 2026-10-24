# Deploy runbook — GCP Cloud Run + Vercel + Neon

Default production target for the ontology engine (vertical #1: podcast ops). This directory holds
the deploy config; the live run itself (milestone M4, task T063) is executed once the accounts and
secrets below exist. CI automates the build + deploy steps (`.github/workflows/`, task T061); the
commands here are the manual equivalent and the source of truth for what CI does.

## Topology

```
          Vercel (apps/web, Next.js)
                  │  NEXT_PUBLIC_API_BASE_URL
                  ▼
      Cloud Run service: podcast-ops-api  ──reads/writes──┐
      (FastAPI; min 0 / max 4; /health probe)             │
                                                          ▼
Cloud Scheduler ──POST :run──► Cloud Run Job:     Neon Postgres + pgvector
   (cron, e.g. 0 */6 * * *)    podcast-ops-ingest  (objects, staging, resolution,
                               (python -m app.jobs) action_attempts, embeddings)
                                                          ▲
                              GCP Secret Manager ─────────┘
                              (DATABASE_URL, API keys, OAuth token, targets)
```

Both the service and the job run the **same image** (`infra/docker/Dockerfile.api`); the job just
overrides the command to the one-shot ingest (`app/jobs.py`).

## One-time setup

Set your shell: `PROJECT_ID=…  REGION=us-central1  REPO=podcast-ops`.

1. **Neon database** — create a project, enable `pgvector` (`CREATE EXTENSION IF NOT EXISTS vector;`),
   copy the pooled connection string as `DATABASE_URL`
   (`postgresql+psycopg://<user>:<pass>@<host>/<db>?sslmode=require`).
2. **Artifact Registry** — `gcloud artifacts repositories create $REPO --repository-format=docker --location=$REGION`.
3. **Secret Manager** — create one secret per row in the table below:
   `printf '%s' "$VALUE" | gcloud secrets create DATABASE_URL --data-file=- --replication-policy=automatic`
   (and `gcloud secrets versions add …` to rotate). Grant the Cloud Run runtime service account
   `roles/secretmanager.secretAccessor`.
4. **Schema** — run the Alembic migration against Neon once:
   `DATABASE_URL=… alembic -c infra/migrations/alembic.ini upgrade head`.

## Secrets (GCP Secret Manager)

| Secret | Used by | Notes |
|---|---|---|
| `DATABASE_URL` | api, job | Neon connection string (pgvector enabled) |
| `YOUTUBE_API_KEY` | api, job | public-metadata read |
| `TARGET_YOUTUBE_SOURCE` | job | the show's YouTube channel id |
| `TARGET_APPLE_SHOW` | job | the show's Apple collectionId |
| `YOUTUBE_OAUTH_TOKEN` (file) | job | writeback token for the **owned** test channel; mount as a file secret at `/secrets/youtube_token.json` |
| `ANTHROPIC_API_KEY` | api | agent; absent → `/agent/ask` returns 503 |
| `VOYAGE_API_KEY` | api, job | embeddings (prod provider) |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | api | tracing (optional) |

No secret is ever committed — `.env`, `secrets/`, and `run/` are gitignored, and the CI security job
(T066) asserts it.

## Deploy

```bash
IMAGE=$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/api:$(git rev-parse --short HEAD)

# 1. Build + push the image (API + job share it)
docker build -f infra/docker/Dockerfile.api -t "$IMAGE" .
docker push "$IMAGE"

# 2. Deploy the API service and the ingest job (manifests substitute PROJECT_ID/REGION/IMAGE_TAG)
export PROJECT_ID REGION IMAGE_TAG=$(git rev-parse --short HEAD)
envsubst < infra/deploy/cloud-run-api.yaml        | gcloud run services replace - --region=$REGION
envsubst < infra/deploy/cloud-run-ingest-job.yaml | gcloud run jobs     replace - --region=$REGION

# 3. Schedule ingestion (see cloud-run-ingest-job.yaml header for the full scheduler command)

# 4. Web → Vercel: set Root Directory to apps/web, NEXT_PUBLIC_API_BASE_URL to the Cloud Run URL;
#    pushes to main auto-deploy (vercel.json).
```

## Verify (T062/T063)

- `GET https://<api-url>/health` → lists the registered ontology (storage: `postgres`).
- `GET https://<api-url>/access/check` → **3/3** (YouTube read, Apple read, YouTube write scope).
- Run `specs/002-ontology-engine/quickstart.md` Scenarios 1–4 against the deployed stack on the real
  show; capture the audit trail. That is the SC-006 live spine and milestone M4's Definition of Done.
