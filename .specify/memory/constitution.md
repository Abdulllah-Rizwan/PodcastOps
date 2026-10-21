<!--
SYNC IMPACT REPORT (scratch — remove before committing the amended constitution)
=================================================================================
Amendment 2026-10-21: 1.0.0 → 1.1.0 (MINOR)
Rationale: The second read platform is changed from Spotify to Apple Podcasts.
The Spotify Web API refused all catalog reads for the operator's app
("Active premium subscription required for the owner of the app"), a hard
external blocker. Apple Podcasts' public iTunes lookup API serves the same full
episodes with no auth, no market, and no Premium gate, so the two-platform
entity-resolution proof is preserved. The pattern, the "exactly two platforms"
rule, and every principle are unchanged; only the named platform differs — hence
MINOR, not MAJOR. See decisions.md (2026-10-21). Sections touched: Principle III,
Principle V, Scope Boundaries, Development Workflow (DoD).

--- original first-ratification report below ---
Version change: (unratified template) → 1.0.0
Rationale: First ratification. The prior file contained only unfilled template
placeholders, so this is the initial adoption of a complete constitution — a
MAJOR (1.0.0) baseline rather than an amendment.

Modified principles:
  - [PRINCIPLE_1_NAME] → I. Narrow Slice, Ship-Not-Learn
  - [PRINCIPLE_2_NAME] → II. Data → Logic → Action Separation
  - [PRINCIPLE_3_NAME] → III. Entity Resolution Is the Hard Core
  - [PRINCIPLE_4_NAME] → IV. Safe, Logged, Mock-First Writeback
  - [PRINCIPLE_5_NAME] → V. Confirm API Access Before Modeling
  - (added)           → VI. High Code Quality & Design Discipline

Added sections:
  - Scope Boundaries & Hard Limits (was [SECTION_2_NAME])
  - Development Workflow, Milestones & Quality Gates (was [SECTION_3_NAME])
  - Governance (filled)

Removed sections: none

Follow-up TODOs: none — all placeholders resolved. Ratification date set to
adoption date 2026-10-21.
=================================================================================
-->

# Podcast Ops-Hub Constitution

<!-- Validation slice: prove one end-to-end spine of the data → logic → action pattern. -->

## Core Principles

### I. Narrow Slice, Ship-Not-Learn

The project MUST deliver the smallest thing that runs end-to-end, not a complete
feature set. A working spine always wins over a polished partial feature. Success is
defined narrowly: the spine runs end-to-end on real data, **once**.

- The goal is to **demonstrate the data → logic → action pattern**, NOT to ship a product.
- This project is NOT, and MUST NOT drift toward: a clip-optimization tool or podcast
  SaaS; a general or reusable "ontology engine"; a multi-platform product; or an actual
  podcast operation (only a throwaway test channel is owned, for writes).
- Scope creep MUST be held at the line. Any change that adds a platform, a model, a
  dashboard, the learning loop, or "make it general" is out of scope for the slice; it
  MUST be named explicitly and deferred rather than absorbed silently.

**Rationale:** The value of this work is proving a pattern cheaply. Breadth or
productization dilutes that proof and converts a validation exercise into an open-ended
build.

### II. Data → Logic → Action Separation

The three stages MUST remain distinct, and their vocabulary MUST be used exactly.
Sloppy wording between stages causes rework and is treated as a defect.

- **Data** — Raw platform data MUST land in a **staging area first**, then be **resolved
  and conformed**, and only then become an **object**. The object is the clean, fused
  result — never the raw inlet. Raw MUST NOT be ingested straight into an object. The
  core object type is `Episode` (an object *type* ≈ a table; an object *instance* ≈ a row).
- **Logic (= function)** — MUST be read-only. It **decides** ("what should we do?") and
  changes nothing. Plain, explicit rules only for this slice: no ML, no forecasting.
- **Action** — the **only** component permitted to change the world. Deciding is not
  acting; the two MUST stay in separate components.

**Rationale:** The entire pattern being validated is this separation. Collapsing stages
(e.g., deciding inside an action, or objectifying raw data) destroys what the slice exists
to prove.

### III. Entity Resolution Is the Hard Core

Correctly matching the same real-world thing (an episode, a guest) across platforms that
use mismatched IDs, titles, and schemas is the central problem this project proves. It
MUST NOT be papered over, stubbed into triviality, or assumed away.

- Fusing one real episode across YouTube and Apple Podcasts into a single `Episode` object is
  **the** entity-resolution proof and MUST be implemented honestly.
- Matching logic MUST be explicit, inspectable, and defensible against realistic
  mismatches — not a naive exact-string equality that happens to work on one example.

**Rationale:** Fusing data from systems we do not own is the hardest and most valuable
part of the pattern. If resolution is faked, the slice proves nothing.

### IV. Safe, Logged, Mock-First Writeback

The single writeback MUST be built behind a seam and mocked first. It MUST only ever
target our own throwaway test channel.

- The action MUST first **log** `"would publish X to Y"` instead of calling the real API.
  The whole spine MUST be shown to move end-to-end in mock mode **before** any real call
  is swapped in.
- The real writeback MUST be **safe** (able to fail and retry) and **logged**.
- Writeback MUST NEVER target anyone else's channel. Exactly one writeback exists in this
  slice (e.g., post a draft clip / update show notes / schedule a post).

**Rationale:** The action is the only thing that mutates external state. A seam plus
mock-first lets the full spine be validated without risk, and restricting writes to a test
channel keeps the exercise safe and ethical.

### V. Confirm API Access Before Modeling

Before any object is modeled, the two platforms MUST be verified to actually permit the
one planned read and the one planned write — quotas, auth, and write scopes included.

- Reads are limited to public metadata of ONE real public show from exactly TWO platforms,
  **YouTube + Apple Podcasts** (plus YouTube public engagement counts). No ownership is needed
  to read, and owner-only data (listen counts, retention curves for a show we do not own) is
  inaccessible and MUST NOT be designed around.
- A writeback a platform forbids MUST NOT be designed. Access is confirmed first (M0),
  then modeling proceeds.

**Rationale:** Modeling against capabilities the platforms do not grant guarantees rework
and dead ends. Confirming access first keeps the design grounded in what is actually possible.

### VI. High Code Quality & Design Discipline

Even as a validation slice, the code MUST be of high quality and follow established best
practices and design patterns. "Narrow" governs scope, never craftsmanship.

- Code MUST favor clear naming, small focused units, and separation of concerns that
  mirrors the data → logic → action boundaries (e.g., distinct modules/seams for ingestion
  & staging, resolution/conforming, decision logic, and the action/writeback).
- Appropriate, well-understood design patterns MUST be applied where they add clarity
  (e.g., Adapter/Gateway for each platform API, Repository for the staging/object store,
  Strategy for the resolution rule, a seam/port for the writeback). Patterns MUST NOT be
  over-applied beyond what the slice needs (YAGNI).
- Dependencies MUST be inverted at external boundaries so platform APIs and the writeback
  are mockable; the mock-first writeback of Principle IV depends on this.
- Code MUST be tested at the level that matters for the spine: the entity-resolution logic
  and the decision rule MUST have automated tests; the writeback seam MUST be exercised in
  mock mode.
- Secrets and credentials MUST NOT be committed; configuration MUST be externalized.
- Readability, consistent style/formatting, and meaningful error handling and logging are
  required, not optional.

**Rationale:** The pattern being proven must be legible to be convincing. Clean structure
and sound patterns make the spine easy to reason about, test, and later extend into the
deferred milestones without a rewrite.

## Scope Boundaries & Hard Limits

These boundaries are non-negotiable for the validation slice:

- **Read:** ONE real, public show, from exactly TWO platforms (YouTube + Apple Podcasts),
  using public metadata plus YouTube public engagement counts.
- **Fuse:** match the same episode across both platforms into one `Episode` object
  (the entity-resolution proof).
- **Logic:** exactly ONE rule/function that produces a decision (e.g., "episode exists on
  Apple Podcasts but has no YouTube clip yet").
- **Action:** exactly ONE writeback, to our own throwaway test channel, mock-logged first
  then real, safe and logged.
- **Explicitly out of scope:** the learning **loop** (performance feeding back into logic);
  the **governance/security** layer; analytics dashboards; extra platforms; ML/forecasting;
  owner-only data for shows we do not own.

Deferred and acknowledged (do NOT build in this slice): the learning loop (later — M4) and
the governance/security layer. These are future milestones, not current work.

## Development Workflow, Milestones & Quality Gates

Work proceeds along ordered milestones. A milestone is complete only when its spine
behavior runs:

- **M0** — Confirm API access for the one read and the one write (Principle V gate).
- **M1** — Read + fuse both platforms into `Episode` objects (entity resolution working).
- **M2** — One function produces a decision.
- **M3** — One action: mock-logged first, then real against the test channel; safe + logged.
- **M4** *(later)* — Close one loop.
- **M5** *(later)* — Widen.

Quality gates applied to every change:

- Scope check: the change stays inside the Scope Boundaries above, or it is named and
  deferred.
- Stage integrity: raw is not ingested into objects; logic stays read-only; only the action
  mutates external state.
- Writeback safety: any writeback is mock-first, test-channel-only, safe, and logged.
- Code quality: Principle VI is satisfied — tests for resolution and the decision rule pass,
  seams remain mockable, no secrets committed.

**Definition of Done (slice):** One run pulls a real show from YouTube + Apple Podcasts, fuses
its episodes correctly, applies the one rule, and executes one safe, logged writeback to the
test channel. If that runs end-to-end, the slice is done. Stop there.

## Governance

This constitution supersedes other practices for the validation slice. `CLAUDE.md` is the
constitution-in-brief and the runtime guidance file; where this document and detailed specs
(SDD) conflict, this constitution governs.

- **Amendments** MUST be documented in this file, with the version bumped and the Sync
  Impact Report updated to record the change and its rationale.
- **Versioning policy** follows semantic versioning:
  - **MAJOR** — backward-incompatible governance or principle removals/redefinitions.
  - **MINOR** — a new principle/section added, or materially expanded guidance.
  - **PATCH** — clarifications, wording, and non-semantic refinements.
- **Compliance review:** every task, spec, plan, and change MUST be checked against these
  principles before it is accepted. Any task drifting toward an out-of-scope outcome MUST be
  stopped and flagged. Complexity beyond the slice MUST be justified against the principles
  or deferred.

**Version**: 1.1.0 | **Ratified**: 2026-10-21 | **Last Amended**: 2026-10-21
