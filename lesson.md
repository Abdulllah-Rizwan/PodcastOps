# Lessons — toward Senior AI Engineer

A running, compact logbook of concepts worth internalizing, surfaced *as this project forces
them*. Each lesson is deliberately short: **title → high-level gist → why it matters here →
a reference code file to dive into**. To go deep on any lesson, open a fresh Claude Code
session and point it at the reference file with a prompt like *"teach me <lesson title> using
<file>"*.

Newest lessons are appended at the bottom. Keep entries terse; the code is the textbook.

---

## 1. Seams & dependency inversion (mock-first I/O)

**Gist**: Put every side-effecting boundary (an external API read, a writeback) behind an
interface (a *port*), and inject the concrete implementation. You then have a `Mock*` and a
`Real*` that satisfy the same port, selectable at runtime.
**Why here**: The constitution demands the writeback be "mock first" — prove the whole spine
moves with a mock that logs `"would publish X to Y"`, then swap in the real API call. This is
only possible because the action is a seam, not a hardcoded call.
**Dig in**: `src/podcast_ops/action/writeback.py` (`WritebackPort`, `MockWriteback`,
`YouTubeWriteback` with injected `video_getter`/`video_updater`).

## 2. Entity resolution as a first-class problem

**Gist**: Matching "the same real thing" across systems with mismatched IDs/titles/schemas is
not string equality. The honest approach is multi-signal: **normalize → block → score → assign
one-to-one above a threshold**. Blocking cuts the O(n·m) comparison space; one-to-one
assignment prevents fan-out and false merges.
**Why here**: It's the declared "hard core" of the project — fusing one episode across YouTube
and Spotify. Faking it (exact title match) would prove nothing.
**Dig in**: `src/podcast_ops/resolve/matcher.py` (normalize, date-blocking, weighted scoring,
greedy one-to-one), and the boundary tests in `tests/unit/test_matcher.py`.

## 3. Pure functions for decisions (read-only logic)

**Gist**: Keep "deciding" separate from "acting". A decision function takes data and returns a
verdict, mutating nothing — which makes it trivially testable and safe to re-run.
**Why here**: The framework splits *logic* (decides) from *action* (changes the world). The
rule is a pure function over `Episode` objects; a test asserts inputs are unchanged after it
runs.
**Dig in**: `src/podcast_ops/logic/decision.py`; read-only proof in
`tests/unit/test_decision.py::test_rule_is_read_only`.

## 4. Idempotency & safe retries for writes

**Gist**: A network write can succeed on the server but time out before you hear back. Safe
writes carry a **marker/idempotency check** so a retry detects "already done" instead of
duplicating. Failures are caught, logged, and retryable — never left half-applied.
**Why here**: The one writeback appends a show-notes marker; running it twice must yield
`skipped_idempotent`, not two posts. The constitution requires the action be "safe (can fail,
retry) and logged."
**Dig in**: `src/podcast_ops/action/writeback.py` (marker check + try/except → `failure`
outcome); `src/podcast_ops/action/audit_log.py` (append-only attempt log);
`tests/integration/test_spine_mock.py` (idempotency + test-channel-only guard).

## 5. Staging vs. objects (never ingest raw into your domain model)

**Gist**: Land raw external payloads in a **staging** layer first; only after resolving and
conforming do they become clean domain **objects**. Keeping the two physically separate makes
provenance inspectable and stops schema drift from leaking into your logic.
**Why here**: `RawPlatformRecord` (staging) is immutable and never read by logic/action;
`Episode` (object) is the fused result. This is the data-stage discipline the constitution
fixes.
**Dig in**: `src/podcast_ops/ingest/records.py` + `staging.py` (raw) vs.
`src/podcast_ops/objects/episode.py` (conformed, validated).

## 6. Auth models: app-only vs. user-delegated

**Gist**: Two common OAuth shapes. **App-only** (Spotify Client-Credentials, YouTube API key)
reads public data with a static secret — no user, no redirect. **User-delegated** (OAuth
Authorization-Code) mints a *token on behalf of a user* who consents in a browser, required for
actions that touch owned resources. Know which your call needs before you design around it.
**Why here**: Reads use app-only; the writeback needs a user-delegated token with the
`youtube.force-ssl` scope, authorized as the test-channel owner. The redirect-URI confusion you
hit comes straight from this distinction (reads ignore it).
**Dig in**: `src/podcast_ops/access_check.py` (all three probes side by side);
`src/podcast_ops/commands/auth.py` (the installed-app consent flow that produces the token).

---

<!-- Append new lessons above this line as they arise: trade-offs made, a custom eval
pipeline, prompt/latency/cost tuning, caching, observability, etc. -->
