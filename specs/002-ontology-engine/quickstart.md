# Quickstart — Validate the Ontology Engine (Vertical #1: Podcast Ops)

A run-and-verify guide proving the feature end-to-end. It validates each user story against the
Success Criteria. Implementation details live in `tasks.md` and the code; this is the validation
path. See [data-model.md](./data-model.md), [contracts/](./contracts/), and [plan.md](./plan.md).

## Prerequisites

- Docker + Docker Compose; Python 3.11+; Node 20+.
- Credentials (local `.env`, never committed): `YOUTUBE_API_KEY`, YouTube OAuth token (via the
  carried-forward `auth` flow) for the owned test channel, `ANTHROPIC_API_KEY` (or an `ant auth`
  profile), and optionally `VOYAGE_API_KEY` (omit to use the local embedding model).
- Carried-forward vertical #1 config (Huberman Lab): `TARGET_YOUTUBE_SOURCE=UC2D2CMWXMOVWx7giW1n3LIg`,
  `TARGET_APPLE_SHOW=1545953110`, write target `TEST_VIDEO_ID=CfRIjrzeGrU`.

## Setup (local)

```
docker compose -f infra/docker/docker-compose.yml up -d    # postgres+pgvector, redis, langfuse
# apply migrations, install engine + vertical + api (editable), install web deps
```

## Scenario 0 — Access gate (Principle V / M0)

```
GET /access/check     (or: podcast-ops check-access)
```
**Expect**: YouTube read ✅, Apple read ✅, YouTube write scope ✅ for the owned test video. Gate must
pass before live runs.

## Scenario 1 — See the fused ontology (US1 → SC-001)

```
POST /ingest/run        # adapter → staging → resolve → object (+embeddings), as a background job
GET  /ingest/jobs/{id}  # wait for status=done; note counts {staged, fused, single_source}
```
Then open the web **ontology explorer**:
- Browse `Episode` instances; confirm episodes present on both platforms show a single fused Episode
  with `source_refs` = [youtube, apple].
- Open a fused Episode → **resolution**: see the `signals[]` that matched (e.g. title similarity,
  date proximity) and a `confidence` value.
- Confirm an Apple-only episode appears as single-source and is **not** falsely fused.

**Pass**: fusion visible with contributing platforms, matched signals, and confidence — all in the
UI, no code. **Verifies**: Principle II (staging precedes objects), III (inspectable resolution).

## Scenario 2 — Decide → approve → act, safely (US2 → SC-003)

```
POST /functions/apple_without_youtube/run     # read-only; returns flagged episodes, mutates nothing
POST /actions/youtube_update_show_notes/preview   # mock: logs "would update show notes on {TEST_VIDEO_ID}"
POST /actions/youtube_update_show_notes/execute   # body {approved:true}: real videos.update
POST /actions/youtube_update_show_notes/execute   # repeat → status skipped_idempotent
GET  /actions/attempts                            # all three attempts recorded with outcomes
```
**Pass**: function changes nothing; mock logs intent only; real writeback succeeds once; retry is
idempotent; every attempt (mock + real) is in the audit trail. **Verifies**: Principle IV; deciding ≠ acting.

## Scenario 3 — Entity resolution is measured (US3 → SC-002/SC-007)

```
POST /evals/resolution/run        # hermetic: JSON backend + local embeddings, no network
GET  /evals/resolution/latest     # precision, recall, F1, mismatched cases, threshold, pass/fail
```
Also run the same entrypoint as the **CI gate**; weaken a matcher rule and confirm the gate fails.
**Pass**: report meets the target (≥95% precision / ≥90% recall) on the golden set and the CI gate
blocks a regression. **Verifies**: Principle III/VI.

## Scenario 4 — Grounded AI agent, propose-only (US4 → SC-004)

```
POST /agent/ask     {"question": "Which episodes are missing a video clip?"}  (streamed)
```
**Expect**: an answer whose `citations[]` are real Episode ids; if the agent suggests fixing one, it
returns a `proposed_action` — and nothing happens externally until:
```
POST /agent/proposals/{id}/approve     # routes through the human-approved action path
```
Ask an ungrounded question → the agent states it lacks grounded data (no fabrication). Confirm a
Langfuse `trace_id` is recorded.
**Pass**: answers cite real objects; zero autonomous external changes; approval required to act.
**Verifies**: Principle VI (grounded + human-in-the-loop + traced).

## Scenario 5 — Engine/vertical seam (SC-005) & deploy (SC-006)

- **Seam**: grep confirms no `engine/` module imports `verticals/podcast`; the podcast types/sources/
  functions/actions appear only via `verticals/podcast/registry.py`. **Verifies**: Principle I.
- **Deploy**: the full spine (Scenarios 1–2) runs against the real show in the deployed environment
  (Cloud Run API + Vercel web + managed Postgres), not only locally. **Verifies**: SC-006.

## Definition-of-Done check

All scenarios pass end-to-end on the real show, in the deployed environment, with eval suites green
in CI. (The engine is only *proven* later, at M5, when a second vertical registers and runs with no
engine change — out of scope for this feature.)
