# Feature Specification: AI-Native Ontology Engine (Vertical #1: Podcast Ops)

**Feature Branch**: `002-ontology-engine`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "Build a reusable, AI-native ontology engine, proven by verticals, with podcast operations as vertical #1 (the live demo). The engine is the product; a vertical is a plugin/configuration on it. Per constitution v2.0.0." (full engine + vertical #1 description as provided)

## Overview

We are building a reusable **ontology engine** that turns messy data from systems we do not own
into clean, fused **objects**, lets read-only **functions** decide what to do, and lets safe,
audited **actions** change the world — with an **AI layer grounded in those objects**. The engine
is the product; a **vertical** is a configuration/plugin on top of it. **Podcast operations is
vertical #1** — the live demo that proves the engine on real, cross-platform data.

The guiding discipline (constitution v2.0.0, Principle I): **generality is earned by a second
vertical, never asserted.** This feature builds the engine *vertical-shaped first*, with clean
engine/vertical seams, and does **not** build a second vertical. The engine must not grow
abstractions that vertical #1 does not use.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the fused ontology for a real show (Priority: P1)

The operator points the podcast vertical at one real, public show that publishes on two platforms.
The system ingests public data from both, resolves which items are the *same real episode* across
platforms, and presents a browsable ontology: object types (Show, Episode, Guest, Clip), the
instances, and the typed links between them. For each fused Episode the operator can see which
platforms contributed, and — crucially — *why* the match was made (which signals matched and at
what confidence).

**Why this priority**: This is the heart of the engine and the showcase. It proves the
data → objects pipeline and the entity-resolution hard core end-to-end, with a real UI, and
delivers standalone value: a clean, inspectable, fused view of a show that neither platform offers
on its own. It is a viable MVP by itself.

**Independent Test**: Run ingestion for the real show, then open the ontology explorer and confirm
episodes appearing on both platforms are fused into single Episode objects, each showing its
contributing platforms, the matched signals, and a confidence value; episodes on only one platform
appear unfused and correctly labelled.

**Acceptance Scenarios**:

1. **Given** a real show published on both platforms, **When** ingestion runs, **Then** raw items
   from each platform land in staging first and only become Episode objects after resolution and
   conforming (no raw item is ever presented as an object).
2. **Given** the same episode exists on both platforms with mismatched IDs and slightly different
   titles, **When** resolution runs, **Then** it produces exactly one fused Episode linking both
   platform sources, with the contributing signals and a confidence score visible.
3. **Given** an episode that exists on only one platform, **When** resolution runs, **Then** it
   remains a single-source Episode and is not falsely fused with any other.
4. **Given** the fused ontology, **When** the operator opens the explorer, **Then** they can browse
   object types, drill into instances, and traverse links (e.g., Episode → Guest, Episode → Clip)
   without reading code.

---

### User Story 2 - Turn a decision into a safe, approved, audited action (Priority: P2)

A read-only function evaluates the fused objects and flags episodes needing attention (for example,
"present on the podcast platform but has no corresponding clip on the video platform yet"). The
operator reviews the flagged decision, and — only on explicit approval — the system performs one
writeback to a channel the operator owns. The action runs in mock mode first (logging exactly what
it *would* do), then for real, is idempotent on retry, and every attempt is recorded.

**Why this priority**: Completes the data → logic → action spine and proves the single most
safety-critical rule of the engine: deciding never changes the world; only an approved, audited
action does.

**Independent Test**: Run the function over the fused objects, confirm it returns a defensible list
of flagged episodes without mutating anything; approve one; confirm a mock run logs the intended
change; confirm a real run performs it against the owned test channel; re-run and confirm no
duplicate effect; confirm all attempts (mock and real) appear in the audit trail with outcomes.

**Acceptance Scenarios**:

1. **Given** fused objects, **When** the decision function runs, **Then** it returns flagged items
   and changes no external state and no object.
2. **Given** a flagged item awaiting approval, **When** no human approves it, **Then** no external
   change occurs.
3. **Given** an approved item in mock mode, **When** the action runs, **Then** it logs "would do X
   to Y" and makes no real external change.
4. **Given** an approved item in real mode, **When** the action runs, **Then** it performs the
   writeback to the owned channel and records the attempt and outcome.
5. **Given** an action that already succeeded, **When** it is retried, **Then** it detects the prior
   effect and does not duplicate it (idempotent), recording the retry as skipped.
6. **Given** a transient failure at the target, **When** the action runs, **Then** it fails safely,
   records the failure, and can be retried.

---

### User Story 3 - Trust entity resolution because it is measured (Priority: P2)

The operator (and anyone evaluating the project) can see how good the entity resolution actually is,
measured against a labeled golden set of known same/different pairs. The system reports
precision/recall-style quality, and a change that degrades resolution quality below an agreed
threshold is caught automatically before it ships.

**Why this priority**: Entity resolution is the hard core (Principle III). Claiming it works is not
enough; it must be measurable and defended against regression. This is what makes the resolution
honest and the whole platform credible.

**Independent Test**: Run the resolution evaluation against the golden set and confirm it reports
precision/recall and the specific pairs it got wrong; deliberately weaken a matcher rule and confirm
the eval flags the regression.

**Acceptance Scenarios**:

1. **Given** a labeled golden set of episode pairs, **When** the resolution eval runs, **Then** it
   reports precision, recall, and the mismatched pairs.
2. **Given** both a deterministic baseline matcher and an upgraded (similarity-based) matcher,
   **When** evaluated on the same golden set, **Then** each is scored on identical cases so they can
   be compared.
3. **Given** a change that lowers resolution quality below the agreed threshold, **When** the eval
   suite runs as part of the change process, **Then** the change is flagged/blocked.

---

### User Story 4 - Ask the AI agent, grounded in the ontology (Priority: P3)

The operator asks a natural-language question about the show, and the AI agent answers using the
actual objects and links (citing which objects the answer came from), not free-form guessing. When
useful, the agent *proposes* an action — but it can never execute an external change on its own; a
human must approve, and the proposal is validated by the engine like any other action.

**Why this priority**: The AI layer is the on-trend showcase capability and the payoff of having an
ontology (grounded, traceable answers; safe, proposed-not-executed actions). It builds on the
objects, functions, and actions from the earlier stories, so it comes after them.

**Independent Test**: Ask a question whose answer depends on fused objects (e.g., "which episodes
are missing a video clip?") and confirm the answer cites specific objects; confirm that when the
agent proposes an action, nothing happens to the external world until a human approves it.

**Acceptance Scenarios**:

1. **Given** a fused ontology, **When** the operator asks a grounded question, **Then** the agent's
   answer references the specific objects/links it used.
2. **Given** a question with no grounding in the ontology, **When** the agent answers, **Then** it
   declines or clearly states it lacks grounded data rather than fabricating.
3. **Given** the agent proposes an action, **When** a human has not approved it, **Then** no external
   change occurs, and the proposal is subject to the same validation and audit as any action.
4. **Given** AI calls are made, **When** they run, **Then** they are traced/observable and covered by
   evals (quality of answers and of proposed actions).

---

### Edge Cases

- **One-sided episodes**: an episode on only one platform must remain unfused, never force-matched.
- **Near-duplicate titles**: two genuinely different episodes with very similar titles/dates must
  not be fused; resolution must distinguish them and the eval must include such hard cases.
- **Source outage / quota**: if a platform read fails or hits quota mid-ingest, the system degrades
  gracefully (keeps prior objects, records the failure) rather than corrupting the object set.
- **Resolution-service unavailable**: if the similarity/embedding path is unavailable, the system
  falls back to the deterministic baseline matcher rather than failing ingestion.
- **Action target error / retry**: a failed real action is recorded and retryable; a repeated action
  must not double-apply.
- **AI proposes an invalid or out-of-policy action**: the engine rejects it at validation; it never
  reaches the external world.
- **Access not granted**: a data source or write target whose read/write has not been confirmed must
  block modeling against it (no designing a forbidden writeback).
- **Empty / first run**: with no prior objects, the first ingest must build the object set from
  scratch without special-casing.

## Requirements *(mandatory)*

### Functional Requirements — Engine (domain-agnostic core)

- **FR-001**: The engine MUST represent an ontology as declared **object types** (≈ tables), their
  **object instances** (≈ rows), and typed **links** between object types; verticals MUST be able to
  register their object types and links declaratively without modifying engine-internal code.
- **FR-002**: The engine MUST ingest source data through a pipeline of source adapter → **staging**
  → resolution/conforming → object. Raw data MUST NOT be presented or stored as an object before
  resolution; the object is always the conformed, fused result.
- **FR-003**: The engine MUST perform **entity resolution** across sources with mismatched IDs,
  titles, and schemas, producing fused objects. Resolution MUST be explicit and inspectable: for
  each match it MUST expose which signals contributed and a confidence value.
- **FR-004**: The engine MUST support a **deterministic baseline matcher** and an upgradeable
  **similarity-based matcher** (embeddings/vector similarity), with the baseline always retained so
  the upgrade can be evaluated against it.
- **FR-005**: The engine MUST provide a registry of **read-only functions** that compute decisions
  over objects and change nothing (no object mutation, no external effect).
- **FR-006**: The engine MUST provide a registry of typed **actions** that are the ONLY path to
  change external state. Every action MUST be mock-first (log intended effect before any real call),
  safe (able to fail and be retried), idempotent (no duplicate effect on retry), and audited (every
  attempt and outcome recorded durably).
- **FR-007**: Actions MUST only target channels the operator owns or is authorized to write to. An
  action MUST NOT be modeled against a target whose write access has not been confirmed.
- **FR-008**: The engine MUST provide an **AI layer grounded in the ontology**: retrieval over
  objects and links (and their embeddings), and an agent that answers from objects and may *propose*
  actions. The AI MUST NOT execute any external change autonomously; every AI-proposed action MUST be
  validated by the engine and approved by a human before execution (human-in-the-loop).
- **FR-009**: The engine MUST provide an **evaluation harness**: precision/recall-style evaluation of
  entity resolution against a labeled golden set, and deterministic plus rubric/judge evaluation of
  AI answers and proposed actions. Eval runs MUST be repeatable on demand.
- **FR-010**: The change process MUST run the eval suites automatically and MUST flag/block a change
  that regresses entity-resolution quality below an agreed threshold.
- **FR-011**: AI interactions MUST be traceable/observable (inputs, grounding used, outputs, proposed
  actions recorded for inspection).
- **FR-012**: The engine MUST expose its capabilities through an application interface (API) consumed
  by the UI and by background processing, with ingestion runnable as a background process.
- **FR-013**: The engine MUST provide a web **ontology explorer** UI: browse object types, drill into
  instances, traverse links, and view per-match confidence and contributing signals.
- **FR-014**: The engine MUST confirm a data source actually permits the planned read/write (quotas,
  auth, scopes) before objects/actions are modeled against it, and MUST surface the result of that
  access check.
- **FR-015**: The engine MUST keep a clean **engine/vertical seam**: engine code MUST NOT contain
  vertical-specific object types, sources, functions, or actions, and MUST NOT grow abstractions no
  current vertical uses (earned-generality discipline).

### Functional Requirements — Vertical #1 (Podcast Ops plugin)

- **FR-016**: Vertical #1 MUST register object types **Show, Episode, Guest, Clip** and their links
  (e.g., Episode features Guest, Episode has Clip, Episode belongs to Show).
- **FR-017**: Vertical #1 MUST ingest one real, public show from **two platforms** — a video platform
  (YouTube, incl. public engagement counts) and a podcast platform (Apple Podcasts) — using public
  metadata only; no ownership is required to read, and owner-only data MUST NOT be designed around.
- **FR-018**: Vertical #1 MUST fuse the same real episode across both platforms into a single Episode
  object (the entity-resolution proof), and MUST seed the resolution golden set from the known
  matched/non-matched pairs already produced by the completed slice.
- **FR-019**: Vertical #1 MUST provide at least one decision function (e.g., "exists on the podcast
  platform but has no corresponding video clip yet").
- **FR-020**: Vertical #1 MUST provide at least one action: a writeback (e.g., update show notes on
  the owned test channel) that is mock-first then real, idempotent, and audited.
- **FR-021**: Vertical #1 MUST provide an ops dashboard view over its objects and decisions, and the
  AI agent MUST operate over the podcast ontology.

### Out of Scope (this feature)

- A **second vertical** (constitution M5) — planned, deliberately **not** built here; it is the
  future generality proof.
- A productized governance/security layer and multi-tenant productization.
- Any data source or write target whose access has not passed the confirmation gate (FR-014).

### Key Entities

**Engine entities**
- **Object Type**: a declared kind of thing in the ontology (≈ table), with properties.
- **Object Instance**: one fused thing (≈ row), produced only after resolution/conforming.
- **Link**: a typed relationship between two object types.
- **Source Adapter**: a connector that reads from one external system into staging.
- **Staging Record**: raw, pre-resolution data held before it can become an object.
- **Resolution/Match Decision**: the record of how sources were fused, the contributing signals, and
  the confidence.
- **Function**: a read-only computation producing a decision over objects.
- **Action**: a typed, validated, mock-first, idempotent, audited external change.
- **Action Audit Record**: durable record of each action attempt and its outcome.
- **Golden Case**: a labeled pair/example used to evaluate resolution (and AI) quality.
- **Agent Query / Grounded Answer**: a question and its answer with cited objects, plus any proposed
  (unexecuted) actions.
- **Vertical**: the registered bundle of object types, sources, functions, actions, and UI views that
  configures the engine for one domain.

**Vertical #1 (podcast) entities**
- **Show**, **Episode**, **Guest**, **Clip**: the podcast domain object types; Episode is the fusion
  target across the two platforms.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a real show published on both platforms, the operator can view each episode fused
  across platforms and, for every fused episode, see the contributing platforms, the matched signals,
  and a confidence value — entirely through the UI, without reading code.
- **SC-002**: Entity resolution, evaluated against the labeled golden set, meets an agreed quality
  bar (target: ≥ 95% precision and ≥ 90% recall), and the score is reproducible on demand and lists
  the specific cases it got wrong.
- **SC-003**: 100% of external changes occur only through a reviewed, human-approved action; 100% of
  action attempts (mock and real) are recorded with their outcome; a retried action causes zero
  duplicate external effects.
- **SC-004**: The AI agent answers show questions with citations to the specific objects used, and
  makes zero autonomous external changes — every AI-proposed action requires explicit human approval
  before it can run.
- **SC-005**: The podcast vertical's object types, sources, functions, and actions are added purely
  by registration/configuration, with no changes to engine-internal code (the engine/vertical seam
  is demonstrably intact).
- **SC-006**: The full spine (ingest → fuse → decide → approve → act) runs on the real show in a
  deployed environment, not only on a developer's machine.
- **SC-007**: The eval suites run automatically on each change and block a change that regresses
  entity-resolution quality below the agreed threshold.

## Assumptions

- **Delivery is milestone-phased** (constitution M0–M4): a thin full-stack skeleton first, then the
  generalized ontology core, then measured resolution, then the AI agent, then hardening/deploy. The
  user stories' priorities (P1→P3) reflect that order. M5 (vertical #2) is out of scope here.
- **The proven slice is the seed**: the existing Python core (source gateways, staging, matcher,
  Episode objects, decision rule, writeback seam + audit log) is reused and generalized into the
  engine rather than rewritten from scratch.
- **Vertical #1 target is a real public show**: configuration from the completed slice (Huberman Lab
  — a specific video channel, a specific podcast show, and an owned test video as the write target)
  carries forward; the write target is a throwaway channel we own.
- **Public-data reads only** for platforms we do not own; owner-only metrics for such shows are
  inaccessible and are not designed around.
- **Technology choices are deferred to planning**: specific stack defaults suggested for planning
  (relational store plus a vector store for embeddings; an API backend over the existing core; a web
  frontend; cloud deployment with automated checks) are implementation decisions for `/speckit-plan`,
  not requirements here, and may be adjusted there.
- **A single operator** uses the system for this feature; multi-user/multi-tenant concerns are out of
  scope.
- **Human-in-the-loop** is acceptable and required for all external changes, including AI-proposed
  ones; fully autonomous action is explicitly not a goal of this feature.
