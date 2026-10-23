# Phase 1 Data Model — AI-Native Ontology Engine

**Feature**: `002-ontology-engine` | **Date**: 2026-10-23

Two layers: **engine** entities (domain-agnostic, the reusable core) and **vertical #1 (podcast)**
entities (registered via the engine, never baked into it). The engine never references podcast
types; the podcast vertical registers its types/links/functions/actions with the engine.

---

## Engine layer (domain-agnostic)

### ObjectType
The declared kind of thing in an ontology (≈ a table).
- `key` (str, unique) — e.g. `"episode"`.
- `properties` — named typed fields with validation (required/optional, type, format).
- `embeddable_fields` (list[str]) — which properties feed the embedding (e.g. title, description).
- `source_bindings` — which source adapters can contribute to this type.
- Rules: `key` unique within an ontology; a property marked identifying participates in blocking.

### Link (LinkType + LinkInstance)
A typed relationship between two ObjectTypes.
- `key` (str), `from_type`, `to_type`, `cardinality` (`one`/`many`).
- Examples (podcast): `episode —features→ guest`, `episode —hasClip→ clip`, `episode —belongsTo→ show`.
- Rule: endpoints must reference registered ObjectTypes; links are directional and inspectable in UI.

### StagingRecord
Raw, pre-resolution data from one source. **Never presented as an object.**
- `id`, `source_key` (e.g. `"youtube"`), `object_type_key`, `external_id`, `raw_payload` (json),
  `fetched_at`, `status` (`staged` → `resolved`/`discarded`).
- Rule (Principle II): an ObjectInstance may only be created from resolved staging records, never
  directly from a raw payload.

### ObjectInstance
One fused thing (≈ a row), produced only after resolution + conforming.
- `id` (engine-assigned), `object_type_key`, `properties` (conformed values),
  `source_refs` (list of `{source_key, external_id}` — which platforms contributed),
  `embedding` (vector, nullable), `created_at`, `updated_at`.
- Rule: `source_refs` has ≥1 entry; a fused instance has ≥2 from different sources.

### ResolutionDecision
The inspectable record of how sources were matched into an instance (the hard-core audit).
- `id`, `object_type_key`, `instance_id`,
  `members` (the staging records / external ids fused),
  `signals` (list of `{name, value, weight, contribution}` — e.g. title_similarity=0.94),
  `confidence` (0–1), `matcher` (`baseline`/`similarity`/`combined`), `decided_at`.
- Rule (Principle III): every fuse of ≥2 sources has a ResolutionDecision exposing signals +
  confidence; single-source instances record "no match found" with the best rejected candidate.

### FunctionDef (read-only)
A registered computation producing a decision over objects.
- `key`, `description`, `input` (which object types/filters it reads), `output` (decision shape).
- Rule (Principle II): executes read-only — no repository writes, no action calls. Enforced by
  passing functions a read-only view of the store.

### ActionDef + ActionAttempt (ActionAuditRecord)
`ActionDef` — a registered, typed external change (the only mutation path).
- `key`, `description`, `input_schema`, `target` (owned channel identity), `idempotency_key_fields`.
`ActionAttempt` — one execution record.
- `id`, `action_key`, `input`, `mode` (`mock`/`real`), `idempotency_key`,
  `requested_by` (operator / agent-proposed+operator-approved), `approved` (bool),
  `status` (`mock_logged`/`success`/`failed`/`skipped_idempotent`), `result`, `attempted_at`.
- Rules (Principle IV): `mock` logs intent and makes no external change; `real` requires
  `approved=true`; a repeat with the same `idempotency_key` yields `skipped_idempotent`; every
  attempt is persisted; `target` must be an owned channel confirmed by access check.

### EmbeddingRecord
- `instance_id`, `object_type_key`, `provider` (`voyage`/`local`), `model`, `vector`, `created_at`.
- Stored in pgvector; indexed for nearest-neighbor candidate generation.

### GoldenCase (eval)
A labeled example for evaluating resolution (and AI).
- `id`, `kind` (`match`/`non_match`), `left_ref`, `right_ref`, `label`, `notes`.
- Seeded from the slice's 199 real matched pairs plus curated hard negatives (near-duplicate
  titles/dates). Used by the ER eval to compute precision/recall/F1 and list mismatches.

### AgentInteraction / GroundedAnswer
- `id`, `question`, `grounding` (object/link ids retrieved), `answer_text`,
  `citations` (object ids referenced), `proposed_actions` (list of unexecuted ActionDef+input),
  `trace_id` (Langfuse), `created_at`.
- Rule (Principle VI): `citations` reference real ObjectInstance ids; `proposed_actions` are never
  auto-executed.

### Vertical (registration)
- `key` (e.g. `"podcast"`), registers: ObjectTypes, LinkTypes, SourceAdapters, FunctionDefs,
  ActionDefs, UI view config, golden set location.
- Rule (Principle I): the engine discovers a vertical only through this registration; no engine
  module imports a vertical module.

### AccessCheckResult
- `source_key`, `capability` (`read`/`write`), `ok` (bool), `detail`, `checked_at`.
- Gate (Principle V): modeling/actions against a source require a passing result.

---

## Vertical #1 (podcast) layer — registered on the engine

### ObjectTypes
- **Show**: `title`, `description`, `publisher`, platform ids. Embeddable: title, description.
- **Episode** (the fusion target): `title`, `description`, `published_at`, `duration_s`,
  `youtube_ref` (video id + public engagement counts), `apple_ref` (episode/collection ids),
  `source_refs`. Embeddable: title, description.
- **Guest**: `name`, aliases. (Linked from Episode; extraction may be later/simple.)
- **Clip**: `title`, `youtube_video_id`, `parent_episode_ref`.

### LinkTypes
- `episode —belongsTo→ show`, `episode —features→ guest`, `episode —hasClip→ clip`.

### SourceAdapters
- **youtube** (read: uploads + public engagement counts; write: `videos.update`), **apple** (read:
  iTunes lookup, no auth). Both implement the engine `SourceAdapter` port (reused slice gateways).

### FunctionDef
- **apple_without_youtube**: Episodes present on Apple with no linked YouTube clip yet → decision
  list. (Reused slice rule, read-only.)

### ActionDef
- **youtube_update_show_notes**: append a marker/show-notes line to the owned test video via
  `videos.update`. Mock-first, idempotent on the marker, audited. `target` = owned test channel.

### Golden set
- `verticals/podcast/evals/golden/` — the 199 matched pairs + hard negatives, loaded as GoldenCases.

---

## Key relationships & invariants (cross-cutting)

- **Pipeline order**: `SourceAdapter → StagingRecord → ResolutionDecision → ObjectInstance`
  (+ EmbeddingRecord). No path creates an ObjectInstance from a raw payload. *(Principle II)*
- **Decide ≠ act**: FunctionDef reads only; state changes only through ActionDef/ActionAttempt.
  *(Principle II/IV)*
- **AI boundary**: AgentInteraction reads via functions/retrieval and can only emit
  `proposed_actions`; turning one into an ActionAttempt requires operator approval. *(Principle VI)*
- **Engine/vertical seam**: all podcast rows above exist only because the `podcast` Vertical
  registered them; engine tables/types carry no podcast-specific columns. *(Principle I)*
- **Measurability**: every multi-source fuse has a ResolutionDecision; GoldenCases make the matcher
  gradeable and regression-gated. *(Principle III/VI)*
