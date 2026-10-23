# Contract — Engine Ports (dependency-inverted seams)

These are the engine's internal interfaces. Each is a port with ≥1 adapter so external systems are
mockable (Principle VII). A vertical supplies adapters by registering them; tests use fakes.

## SourceAdapter (ingestion inlet)
*(generalized from the slice's youtube/apple gateways)*
```
read(config) -> Iterable[StagingRecord]        # raw → staging only; never returns ObjectInstances
capabilities() -> {read: bool, write: bool}    # feeds the access check
confirm_access(capability) -> AccessCheckResult # Principle V gate
```
- Contract: `read` yields raw payloads tagged with `source_key`, `external_id`, `object_type_key`.
  It MUST NOT create objects. Idempotent re-reads are allowed (staging dedupes by external id).

## Matcher (resolution strategy)
```
block(records) -> candidate_groups             # cheap candidate generation
score(candidate) -> {signals[], confidence}    # per-signal contributions + confidence
```
- Two implementations always coexist: `BaselineMatcher` (deterministic, rapidfuzz) and
  `SimilarityMatcher` (embedding cosine via pgvector). `CombinedMatcher` merges them into a
  `ResolutionDecision`. Baseline MUST remain runnable alone for eval comparison (Principle III).

## EmbeddingProvider
```
embed(texts: list[str]) -> list[vector]
model_id() -> str
```
- Adapters: `VoyageEmbeddings` (default), `LocalEmbeddings` (sentence-transformers, offline/CI).
  Selected by config; the ER eval uses the local adapter so CI is hermetic and free.

## Repository (object/staging/audit store)
*(generalized from the slice's objects/repository)*
```
stage(record) / list_staging(...) 
upsert_instance(instance) / get_instance(id) / query_instances(type, filters, page)
save_resolution(decision) / get_resolution(instance_id)
record_attempt(attempt) / find_attempt(idempotency_key) / list_attempts(...)
save_embedding(rec) / nearest(type, vector, k)
read_view() -> ReadOnlyStore                   # the handle functions receive (no write methods)
```
- Backends: `PostgresRepository` (pgvector) and `JsonRepository` (hermetic tests/offline). Functions
  only ever receive `read_view()` — they have no handle that can write (Principle II enforced by type).

## Action port (the only mutation path)
*(generalized from the slice's writeback seam + audit log)*
```
preview(action_key, input) -> ActionAttempt(mode=mock)     # logs intent, no external call
execute(action_key, input, *, approved: bool) -> ActionAttempt(mode=real)
```
- Contract (Principle IV): `execute` refuses unless `approved` is true and the target passed a write
  access check; computes the idempotency key and returns `skipped_idempotent` on repeat; persists
  every attempt via `record_attempt`; `preview` never calls the external API.

## FunctionDef (read-only logic)
```
run(read_view: ReadOnlyStore, params) -> Decision
```
- Contract: pure read; returns a decision structure; MUST NOT touch the Action port or a writable
  repository handle.

## Tracing
```
trace(name) -> span       # wraps AI calls + eval runs; Langfuse adapter (OTel alternative)
```
