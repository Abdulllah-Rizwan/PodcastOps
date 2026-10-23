<!--
SYNC IMPACT REPORT (scratch — remove before committing the amended constitution)
=================================================================================
Amendment 2026-10-23: 1.1.0 → 2.0.0 (MAJOR)
Rationale: The project is redefined. It was a deliberately narrow, throwaway
validation slice whose success was "the spine runs once" and which explicitly
forbade a general/reusable ontology engine, ML, and productization. Having proven
the data → logic → action spine end-to-end on live data, the owner has decided to
build the real thing it was a proof of: a reusable, AI-native **ontology engine**
(objects, links, functions, actions), demonstrated by verticals — the podcast
operation becomes vertical #1, and a second, different vertical later proves the
engine is genuinely general. This is a full-stack build (web UI, API backend,
Postgres + vector store, AI agent, evals, cloud deployment). Three former hard
boundaries are REVERSED — "NOT a general/reusable ontology engine," "no ML," and
"narrow slice / runs once / not a product" — so this is MAJOR, not MINOR.

What SURVIVES (still non-negotiable): the Data → Logic → Action stage separation;
"entity resolution is the hard core"; safe, logged, mock-first actions; confirm
access before modeling; high code quality & design discipline.
What is ADDED: engine-first discipline (generality earned by vertical #2, never
asserted ahead of need); AI grounded in the ontology and evaluated.
What is REMOVED/REDEFINED: ship-it-once success criterion; the anti-generality,
anti-ML, anti-product limits; the slice's "exactly one of everything" caps.

Version change: 1.1.0 → 2.0.0
Modified principles:
  - I.  Narrow Slice, Ship-Not-Learn        → I.  Engine First, Proven by Verticals
  - II. Data → Logic → Action Separation     → II. The Ontology: Objects, Links,
                                                   Functions, Actions (retained, generalized)
  - III. Entity Resolution Is the Hard Core  → III. Entity Resolution Is the Hard Core (retained)
  - IV. Safe, Logged, Mock-First Writeback   → IV. Safe, Logged, Mock-First Actions (retained,
                                                   generalized to typed Actions + human-in-loop)
  - V.  Confirm API Access Before Modeling   → V.  Confirm Access Before Modeling (retained)
  - VI. High Code Quality & Design Discipline → VII. High Code Quality & Full-Stack Design
                                                   Discipline (retained, extended full-stack)
  - (added)                                  → VI. AI Grounded in the Ontology, and Evaluated
Added sections: none new by name — "Scope Boundaries & Hard Limits" is rewritten as
  "Scope, Architecture & Hard Limits"; milestones re-baselined.
Removed sections: none.
Follow-up TODOs:
  - CLAUDE.md is the constitution-in-brief and still describes the narrow slice; it
    MUST be rewritten to match this v2.0.0 before the next task.
  - decisions.md MUST get a deviation entry recording this pivot.
  - A fresh Spec Kit cycle (/speckit-specify) MUST define the new scope.
=================================================================================
-->

# Podcast Ops-Hub Constitution

<!-- Build a reusable, AI-native ontology engine (objects → functions → actions), proven by verticals. -->

## Core Principles

### I. Engine First, Proven by Verticals

The product is a **reusable ontology engine**, not any single application. A *vertical*
(a concrete domain wired into the engine) exists to prove the engine on real, messy data —
it is never the end in itself.

- The engine owns the generic machinery: the object/link registry, read-only functions, typed
  actions, the ingestion/resolution pipeline, the API, and the AI runtime. A vertical owns only
  its specifics: which object types, which data sources, which functions, which actions, and its
  UI views. Vertical specifics MUST NOT leak into the engine.
- **Generality MUST be earned, never asserted.** The engine MUST be built vertical-shaped first,
  with clean seams, and MUST NOT be abstracted ahead of a demonstrated second need (YAGNI applied
  to generality). A capability is "general" only once a **second, different vertical** runs on the
  same engine without an engine rewrite. One vertical is a demo; two verticals on one engine are
  the proof.
- **Podcast operations is vertical #1** and MUST remain working end-to-end at all times as the
  engine evolves. A working spine always wins over a half-finished layer.
- This project IS now: a general ontology engine, an AI-native operational platform, and a
  candidate product. The former prohibitions on generality, ML, and productization are lifted by
  this amendment — but only under the earned-generality discipline above.

**Rationale:** The value and the market story are the engine. Building a general platform in the
abstract, with no real user, is the classic trap that produces a worse Foundry and proves nothing;
proving one engine against two honest verticals is what makes the claim credible.

### II. The Ontology: Objects, Links, Functions, Actions (Data → Logic → Action)

The data → logic → action separation is the engine's spine and MUST remain exact. Sloppy wording
or collapsed stages are treated as defects.

- **Data → Objects.** Raw platform data MUST land in a **staging area first**, then be **resolved
  and conformed**, and only then become an **object**. The object is the clean, fused result —
  never the raw inlet; raw MUST NOT be ingested straight into an object. The engine models
  **object types** (≈ tables), **object instances** (≈ rows), and typed **links** between object
  types (e.g., `Episode —features→ Guest`, `Episode —hasClip→ Clip`). `Episode` is vertical #1's
  core object type.
- **Logic = Functions.** Functions MUST be read-only. They **decide** ("what should we do?") and
  change nothing. The engine MUST support an inspectable registry of functions.
- **Action.** Actions are the **only** component permitted to change the world. Deciding is not
  acting; the two MUST stay in separate components. Actions MUST be typed, validated, and recorded
  (see Principle IV).
- Object types, links, functions, and actions MUST be declared **declaratively** in the engine's
  registries, so a vertical adds them as configuration/plugins rather than by editing engine core.

**Rationale:** This separation — objects, read-only functions, mutating actions — is the ontology
model itself. Collapsing stages (deciding inside an action, or objectifying raw data) destroys the
very pattern the engine exists to provide.

### III. Entity Resolution Is the Hard Core

Correctly matching the same real-world thing (an episode, a guest) across systems that use
mismatched IDs, titles, and schemas is the engine's central, most valuable capability. It MUST NOT
be papered over, stubbed into triviality, or assumed away.

- Fusing one real episode across YouTube and Apple Podcasts into a single `Episode` object is
  vertical #1's entity-resolution proof and MUST be implemented honestly.
- Matching MUST be explicit, inspectable, and defensible against realistic mismatches — never a
  naive exact-string equality that happens to work on one example. Where embeddings/vector
  similarity are used, a deterministic baseline matcher MUST be retained to evaluate against.
- Resolution quality MUST be measurable (see Principle VI): the engine MUST expose which signals
  contributed to a match and at what confidence.

**Rationale:** Fusing data from systems we do not own is the hardest and most valuable part of the
pattern. If resolution is faked, every vertical built on the engine proves nothing.

### IV. Safe, Logged, Mock-First Actions

Every action — the only path that mutates external state — MUST be built behind a seam, mocked
first, and only ever target channels the operator owns or is authorized to write to.

- An action MUST first **log** its intent (`"would publish X to Y"`) instead of calling the real
  API. The full spine MUST be shown to move end-to-end in mock mode **before** any real call is
  swapped in.
- Real actions MUST be **safe** (able to fail and retry), **idempotent** (no duplicate effects on
  retry), and **audited** (every attempt and outcome logged durably).
- Actions MUST NEVER target channels the operator does not own or control. Any action proposed by
  an AI component MUST pass the engine's validation and MUST be gated by human approval before it
  executes (human-in-the-loop); AI MUST NOT execute an unvalidated, unapproved mutation.

**Rationale:** The action is the only thing that changes the world. A seam plus mock-first lets the
whole spine be validated without risk; idempotency and audit make real writes safe; restricting
targets and requiring approval for AI-proposed actions keeps the platform safe and ethical.

### V. Confirm Access Before Modeling

Before any object or action is modeled against a data source, that source MUST be verified to
actually permit the planned read or write — quotas, auth, and scopes included.

- Reads of platforms we do not own are limited to data those platforms make available (e.g., public
  metadata, public engagement counts). Owner-only data for a show we do not own (private listen
  counts, retention curves) is inaccessible and MUST NOT be designed around.
- An action a platform forbids MUST NOT be designed. Access is confirmed first, then modeling
  proceeds. This gate applies to every new data source a vertical introduces.

**Rationale:** Modeling against capabilities the platforms do not grant guarantees rework and dead
ends. Confirming access first keeps every vertical grounded in what is actually possible.

### VI. AI Grounded in the Ontology, and Evaluated

AI/LLM capabilities MUST be grounded in the typed ontology and MUST be evaluated — ungrounded
free-form behavior and unmeasured AI are defects.

- AI components (agents, retrieval, generation) MUST read the world through objects, links, and
  functions, and MUST change the world only through validated actions (Principle IV). The LLM
  proposes; the engine validates and records; a human approves mutations.
- Retrieval that feeds an LLM MUST be grounded in the ontology (objects and their links / their
  embeddings), not in unstructured dumps, so answers are traceable to real objects.
- **Evaluation is mandatory, not optional.** Entity resolution MUST have precision/recall-style
  evals against a labeled golden set. AI generation and action-selection MUST have evals
  (deterministic checks plus rubric/LLM-as-judge where appropriate). AI calls MUST be traced/
  observable. Eval suites MUST run in CI and gate changes against regression.

**Rationale:** An ontology exists precisely to make AI reliable — typed objects and validated
actions replace hallucination. Grounding plus evaluation is what separates an engineering platform
from a demo, and it is the capability this project exists to showcase.

### VII. High Code Quality & Full-Stack Design Discipline

The engine and every vertical MUST be high quality across the full stack. "Reusable" and
"shippable" govern scope; they never excuse weak craft.

- Structure MUST mirror the engine/vertical seam and the data → logic → action boundaries: distinct
  modules for ingestion & staging, resolution/conforming, functions, actions, the API, the AI
  runtime, and each vertical's plugin. The engine/vertical boundary MUST be enforced, not aspirational.
- Well-understood patterns MUST be applied where they add clarity (Adapter/Gateway per data source;
  Repository for the object/staging store; Strategy/registry for functions and resolution; a port/
  seam for actions). Patterns MUST NOT be over-applied beyond need (YAGNI).
- Dependencies MUST be inverted at external boundaries (platform APIs, the writeback target, the
  LLM provider, the vector store) so they are mockable; mock-first actions and offline evals depend
  on this.
- Tests are required where they matter: entity resolution and functions MUST have automated tests;
  the action seam MUST be exercised in mock mode; AI behavior MUST have the evals of Principle VI.
- The web frontend, API backend, database/vector layer, and deployment MUST meet the same bar:
  clear naming, meaningful error handling and logging, consistent style/formatting.
- Secrets and credentials MUST NOT be committed; configuration MUST be externalized; production
  secrets MUST use a secret manager, not committed `.env` files.

**Rationale:** The pattern being proven must be legible across the whole stack to be convincing.
Clean structure, enforced seams, and sound patterns make the engine easy to reason about, test,
deploy, and extend into a second vertical without a rewrite.

## Scope, Architecture & Hard Limits

The engine and vertical #1 are full-stack. These boundaries are non-negotiable:

- **Architecture layers (all in scope):** a web **UI** (ontology explorer + the vertical's ops
  dashboard + the AI agent); an **API backend** over the ontology core; a **database** for objects/
  staging plus a **vector store** for embeddings (default: Postgres + pgvector); a **background
  worker** for ingestion; an **AI layer** (grounded retrieval + agent); an **eval + observability**
  harness; and **cloud deployment** with CI/CD.
- **Engine vs vertical (the hard seam):** the engine is domain-agnostic; a vertical is a plugin/
  configuration. Vertical #1 = podcast ops: object types (`Show`, `Episode`, `Guest`, `Clip`),
  data sources (YouTube + Apple Podcasts), its functions, its actions, its UI views.
- **Entity-resolution proof** (Principle III) MUST be preserved in vertical #1: match one real
  episode across YouTube and Apple Podcasts into one `Episode` object.
- **Actions** MUST obey Principle IV (mock-first, safe, idempotent, audited, owned-target-only,
  human-approved for AI-proposed mutations).
- **Earned generality (Principle I):** the engine MUST NOT grow abstractions no current vertical
  uses. Vertical #2 (a different domain) is the generality proof and is planned, not yet built;
  introducing it is a deliberate, logged milestone (M5), not silent engine creep.
- **Still explicitly out of scope** until deliberately chosen and logged: the governance/security
  layer as a product feature; multi-tenant productization; and any data source whose read/write
  has not passed the Principle V access gate.

## Development Workflow, Milestones & Quality Gates

Work proceeds along ordered milestones. A milestone is complete only when its behavior runs
end-to-end (the ship-not-learn spirit is retained even though "runs once" is not the success bar).

- **M0** — Full-stack skeleton: API backend over the existing core, Postgres storage, a minimal UI,
  containerized and deployed thin. Prove the stack moves (echoes mock-first) before adding AI.
- **M1** — Ontology core generalized: declarative object/link/function/action registries; podcast
  object types defined as a vertical plugin on the engine.
- **M2** — Entity resolution upgraded (embeddings + vector store) with evals: precision/recall
  against a labeled golden set (seeded from the real matched pairs already produced).
- **M3** — AI agent over the ontology: grounded retrieval + answers; proposes validated, audited,
  human-approved actions; AI evals + tracing in place.
- **M4** — Harden & deploy for real: CI/CD with the eval gate, observability, secret management,
  autoscale; the UI complete (explorer + ops dashboard + agent).
- **M5** — Vertical #2: a second, different domain runs on the same engine with no engine rewrite —
  the generality proof.

Quality gates applied to every change:

- **Scope & seam check:** the change respects the engine/vertical boundary; no vertical specifics
  leak into the engine, and no speculative generality is added ahead of a real second need, or it is
  named and deferred.
- **Stage integrity:** raw is not ingested into objects; functions stay read-only; only validated
  actions mutate external state.
- **Action safety:** any action is mock-first, owned-target-only, safe, idempotent, audited, and —
  if AI-proposed — human-approved.
- **AI grounding & evals:** AI reads via the ontology and writes only via actions; the relevant eval
  suites pass and gate the change; AI calls are traced.
- **Code quality:** Principle VII is satisfied — tests for resolution and functions pass, seams
  remain mockable, no secrets committed.

**Definition of Done (current build):** The engine runs the podcast vertical full-stack in the
cloud — UI → API → ontology (objects fused by honest entity resolution) → AI grounded in the
ontology → a safe, idempotent, audited, human-approved action — with eval suites green in CI. The
**engine is proven** only when a second, different vertical (M5) runs on it with no engine rewrite.

## Governance

This constitution supersedes other practices for the project. `CLAUDE.md` is the constitution-in-brief
and the runtime guidance file; where this document and detailed specs (SDD) conflict, this
constitution governs.

- **Amendments** MUST be documented in this file, with the version bumped and the Sync Impact Report
  updated to record the change and its rationale. A deviation from the agreed plan MUST also be
  logged in `decisions.md`.
- **Versioning policy** follows semantic versioning:
  - **MAJOR** — backward-incompatible governance or principle removals/redefinitions.
  - **MINOR** — a new principle/section added, or materially expanded guidance.
  - **PATCH** — clarifications, wording, and non-semantic refinements.
- **Compliance review:** every task, spec, plan, and change MUST be checked against these principles
  before it is accepted. Any task that silently widens the engine with unearned generality, collapses
  a stage, or ships an unsafe/ungrounded/unevaluated action MUST be stopped and flagged. Complexity
  beyond what a current vertical needs MUST be justified against these principles or deferred.

**Version**: 2.0.0 | **Ratified**: 2026-10-21 | **Last Amended**: 2026-10-23
