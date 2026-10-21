# Feature Specification: Podcast Ops-Hub Validation Slice

**Feature Branch**: `001-podcast-ops-slice`

**Created**: 2026-10-21

**Status**: Draft

**Input**: User description: "The validation slice defined in CLAUDE.md and the project constitution — prove one end-to-end spine of the data → logic → action pattern: read one real public show from YouTube + Spotify, fuse its episodes into `Episode` objects (entity resolution), apply exactly one decision rule, and execute exactly one safe, logged writeback to our own throwaway test channel."

## User Scenarios & Testing *(mandatory)*

The "user" here is the operator running the slice to demonstrate the pattern (not an end
consumer of a podcast product). Each story is a stage of the data → logic → action spine
and is independently testable.

### User Story 1 - Fuse one show's episodes across two platforms (Priority: P1)

The operator points the system at one real, public podcast that is published on both
YouTube and Spotify. The system pulls public metadata from each platform into a staging
area, resolves and conforms it, and produces a set of clean, fused `Episode` objects — one
object per real-world episode, each carrying both its YouTube identity and its Spotify
identity. This is the entity-resolution proof.

**Why this priority**: Entity resolution is the hard core of the project. Fusing the same
real-world episode across platforms that use mismatched IDs, titles, and schemas is the
single thing most worth proving; nothing downstream is meaningful without it. On its own it
already delivers a demonstrable result: a correctly merged object set.

**Independent Test**: Run the ingest + fuse step against the chosen show and inspect the
resulting `Episode` objects. It passes if each fused object correctly unites the matching
YouTube and Spotify entries for the same episode, with no false merges and no missed
matches across the show's episodes.

**Acceptance Scenarios**:

1. **Given** a real public show present on both YouTube and Spotify, **When** the operator
   runs ingestion, **Then** raw metadata from each platform first lands in a staging area,
   distinct from any `Episode` object.
2. **Given** staged raw metadata from both platforms, **When** resolution and conforming
   run, **Then** each real-world episode becomes exactly one `Episode` object carrying both
   its YouTube and Spotify identities.
3. **Given** two episodes with similar but non-identical titles, **When** resolution runs,
   **Then** they are not falsely merged into one object.
4. **Given** an episode present on one platform but not (yet) the other, **When** resolution
   runs, **Then** it produces one `Episode` object recording which platform it is missing from.

---

### User Story 2 - Produce one decision from the fused objects (Priority: P2)

With `Episode` objects available, the operator runs one read-only rule that inspects each
object and produces a decision — for example, "this episode exists on Spotify but has no
corresponding YouTube clip yet." The rule decides; it changes nothing.

**Why this priority**: This is the "logic" stage of the spine. It is small but proves that
a decision is derived from fused objects and is cleanly separated from any action. It
depends on Story 1's objects existing.

**Independent Test**: Run the rule over a known set of `Episode` objects and confirm it
flags exactly the episodes that satisfy the rule's condition and no others, while leaving
all objects and external state unchanged.

**Acceptance Scenarios**:

1. **Given** a set of fused `Episode` objects, **When** the decision rule runs, **Then** it
   returns a decision for each object (act / do-not-act) based solely on the object's data.
2. **Given** the decision rule runs, **When** it completes, **Then** no `Episode` object and
   no external platform state has been modified (the rule is read-only).
3. **Given** an episode that already satisfies the "done" condition, **When** the rule runs,
   **Then** that episode is not selected for action.

---

### User Story 3 - Execute one safe, logged writeback (Priority: P3)

For an episode the rule selected, the operator triggers exactly one writeback to our own
throwaway test channel (for example: post a draft clip, update show notes, or schedule a
post). The action runs in mock mode first — logging `"would publish X to Y"` instead of
calling the real API — and only after the whole spine is shown to move is the real call
swapped in against the test channel. The action is safe (can fail and retry) and logged.

**Why this priority**: This is the "action" stage — the only thing that changes the world —
and it completes the end-to-end spine. It is last because it depends on both a fused object
and a decision, and because it carries the only external-write risk.

**Independent Test**: With a selected episode, run the action in mock mode and confirm it
logs the intended writeback without calling the external API; then run it in real mode
against the test channel and confirm the change appears there, with both attempts logged and
a failed attempt retryable.

**Acceptance Scenarios**:

1. **Given** an episode selected by the rule, **When** the action runs in mock mode,
   **Then** it logs `"would publish X to Y"` and makes no external API call.
2. **Given** the full spine has been validated in mock mode, **When** the action runs in real
   mode, **Then** it performs exactly one writeback to our own test channel and logs the result.
3. **Given** the real writeback fails, **When** the failure occurs, **Then** the failure is
   logged and the action can be retried without corrupting state or producing a duplicate.
4. **Given** any writeback request, **When** the target is evaluated, **Then** it targets only
   our own throwaway test channel and never any third party's channel.

---

### Edge Cases

- **Title/ID mismatch**: An episode's YouTube title differs from its Spotify title (extra
  tags, episode numbering, sponsor prefixes). Resolution must still match them to one object.
- **One-sided presence**: An episode exists on Spotify but not YouTube (or vice versa). It
  becomes one `Episode` object that records the missing side — this is exactly the condition
  the decision rule looks for.
- **Duplicate/near-duplicate entries** on a single platform (e.g., a re-upload). Resolution
  must not fan these into multiple objects or merge genuinely distinct episodes.
- **Unavailable or rate-limited platform read**: Ingestion of one platform fails or is
  throttled. The staging step must surface the failure rather than silently produce partial
  objects treated as complete.
- **Owner-only data requested**: A rule or report asks for listen counts / retention of a
  show we do not own. This data is inaccessible and must not be depended on.
- **Writeback partial failure / retry**: The real writeback times out after possibly
  succeeding. Retry must not create a duplicate post on the test channel.

## Requirements *(mandatory)*

### Functional Requirements

**Data stage (read + stage + resolve + conform → object)**

- **FR-001**: System MUST read public metadata for ONE real, public show from exactly two
  platforms — YouTube and Spotify — including YouTube public engagement counts.
- **FR-002**: System MUST land raw platform data in a staging area first, kept distinct from
  any `Episode` object; raw data MUST NOT be written directly into an object.
- **FR-003**: System MUST resolve and conform staged data before producing objects, so an
  `Episode` object is the clean, fused result rather than a raw inlet.
- **FR-004**: System MUST match the same real-world episode across YouTube and Spotify into a
  single `Episode` object (entity resolution), uniting both platform identities.
- **FR-005**: System MUST avoid false merges (distinct episodes merged into one) and missed
  matches (the same episode split across two objects) for the chosen show.
- **FR-006**: System MUST record, on each `Episode` object, which platforms the episode is
  present on and which it is missing from.
- **FR-007**: System MUST NOT depend on owner-only data (e.g., listen counts or retention
  curves for a show we do not own), as it is inaccessible.

**Logic stage (decide)**

- **FR-008**: System MUST provide exactly one decision rule/function that reads `Episode`
  objects and produces a decision (e.g., "exists on Spotify but has no YouTube clip yet").
- **FR-009**: The decision rule MUST be read-only: it MUST NOT modify any `Episode` object or
  any external platform state.
- **FR-010**: The decision rule MUST use plain, explicit rules only — no machine learning and
  no forecasting in this slice.
- **FR-011**: Deciding MUST be kept separate from acting; the component that decides MUST NOT
  be the component that writes back.

**Action stage (one safe, logged writeback)**

- **FR-012**: System MUST provide exactly one writeback action, targeting only our own
  throwaway test channel, and NEVER any third party's channel.
- **FR-013**: The writeback MUST be built behind a seam that supports a mock mode which logs
  `"would publish X to Y"` instead of calling the real platform API.
- **FR-014**: System MUST be demonstrable end-to-end in mock mode before the real writeback
  call is enabled.
- **FR-015**: The real writeback MUST be safe — able to fail and be retried without
  corrupting state or creating duplicate posts.
- **FR-016**: Every writeback attempt (mock or real, success or failure) MUST be logged.

**Access confirmation & scope**

- **FR-017**: Before any object is modeled, System MUST confirm that both platforms permit the
  one planned read and the one planned write (quotas, auth, and write scopes).
- **FR-018**: System MUST remain within the slice scope: no additional platforms, no analytics
  dashboard, no learning loop, no governance/security layer, no ML. Any drift toward these MUST
  be flagged and deferred rather than built.

### Key Entities *(include if feature involves data)*

- **Raw Platform Record (staging)**: An untransformed metadata record as pulled from a single
  platform (YouTube or Spotify). Lives only in the staging area. Carries the platform's native
  IDs, titles, and available public fields. Never treated as a finished object.
- **Episode (object)**: The clean, fused result representing one real-world episode. Unites the
  matching YouTube and Spotify identities, records which platforms it appears on and which it is
  missing from, and holds the conformed public metadata (and YouTube public engagement counts).
  Type ≈ a table; instance ≈ a row.
- **Decision**: The read-only output of the single rule for a given `Episode` — whether the one
  action applies (e.g., "needs a YouTube clip") — carrying enough context to drive the action.
- **Writeback Attempt (log record)**: A record of one action attempt — target (always the test
  channel), mode (mock or real), intended change, outcome (success/failure), and timestamp —
  supporting safe retry and auditability.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In one end-to-end run, the system pulls the chosen show from both YouTube and
  Spotify, fuses its episodes, applies the one rule, and performs one safe, logged writeback to
  the test channel — the entire spine completes.
- **SC-002**: Entity resolution is correct for 100% of the chosen show's episodes: every
  real-world episode present on both platforms maps to exactly one `Episode` object, with zero
  false merges and zero missed matches.
- **SC-003**: The decision rule selects exactly the episodes meeting its condition and no
  others, and leaves every `Episode` object and all external state unchanged.
- **SC-004**: The writeback runs in mock mode with zero real external calls before any real
  call is enabled; in real mode it produces exactly one change on the test channel and zero
  changes anywhere else.
- **SC-005**: A simulated writeback failure can be retried to success without creating a
  duplicate post, and both the failure and the retry appear in the logs.
- **SC-006**: Platform access for the one read and the one write is confirmed before object
  modeling begins (no modeling against capabilities a platform does not grant).

## Assumptions

- The operator has selected one real, public show that is published on both YouTube and
  Spotify, and is content to treat its public metadata as the only data source.
- Reading public metadata (plus YouTube public engagement counts) requires no ownership of the
  chosen show; only the writeback requires ownership, and that targets our own throwaway test
  channel.
- A throwaway test channel owned by the project exists (or will be created) as the sole
  writeback target; no third-party channel is ever written to.
- The single decision rule and single writeback are chosen to be the smallest pair that proves
  the spine (e.g., "no YouTube clip yet" → "post a draft clip / update show notes / schedule a
  post"); the exact pair may be finalized during planning without widening scope.
- Platform API quotas and write scopes are sufficient for one read and one write; this is
  verified at milestone M0 before modeling (per FR-017).
- The learning loop and the governance/security layer are explicitly deferred to later
  milestones (M4+) and are out of scope here.
- Success is defined as the spine running end-to-end on real data once; productization,
  generality, extra platforms, and dashboards are out of scope.
