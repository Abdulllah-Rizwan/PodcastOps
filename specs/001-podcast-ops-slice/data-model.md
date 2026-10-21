# Phase 1 Data Model: Podcast Ops-Hub Validation Slice

Derived from the spec's Key Entities and the data → logic → action stages. The guiding rule
(Principle II): **raw → staging → resolve + conform → object**. Raw records never become objects
directly; the `Episode` object is the clean, fused result.

---

## 1. RawPlatformRecord (staging layer)

An untransformed public-metadata record from one platform. Lives only in staging.

| Field | Type | Notes |
|-------|------|-------|
| `platform` | enum(`youtube`,`apple`) | Source platform |
| `platform_id` | str | Native ID (YouTube videoId / Apple episode trackId) |
| `title` | str | Native title/name |
| `description` | str \| null | Native description/show notes |
| `published_at` | date | Native publish/release date |
| `duration_seconds` | int \| null | From YouTube `contentDetails` / Apple `trackTimeMillis` |
| `engagement` | object \| null | YouTube only: `{views, likes, comments}` (public counts) |
| `raw` | object | Full original payload, retained verbatim for traceability |
| `fetched_at` | datetime | When ingested |

**Rules**: persisted under `run/staging/{platform}/`. Immutable once written. Never read by the
logic or action stages — only by the resolver.

---

## 2. Episode (object layer)

The fused, conformed result — one per real-world episode. Produced only by the resolver.

| Field | Type | Notes |
|-------|------|-------|
| `episode_id` | str | Stable internal id (derived, e.g. hash of normalized title + date) |
| `title` | str | Conformed canonical title |
| `published_at` | date | Conformed release date |
| `duration_seconds` | int \| null | Conformed duration |
| `youtube` | PlatformRef \| null | Present iff matched on YouTube |
| `apple` | PlatformRef \| null | Present iff matched on Apple Podcasts |
| `present_on` | list[enum] | Platforms this episode appears on |
| `missing_from` | list[enum] | Platforms this episode is absent from (drives the rule) |
| `match_confidence` | float \| null | Resolver score for the YT↔Apple match (null if one-sided) |

**PlatformRef** (embedded): `{platform, platform_id, url, title, engagement?}`.

**Rules / validation**:
- At least one of `youtube` / `apple` MUST be set.
- `present_on` + `missing_from` MUST together equal {youtube, apple} with no overlap.
- A two-sided `Episode` MUST carry exactly one YouTube ref and one Apple ref (no fan-out —
  Principle III: no false merge, no missed match).
- Persisted to `run/objects/episodes.json`.

---

## 3. Decision (logic layer output)

Read-only output of the one rule for a given `Episode`. Produced by `logic/decision.py`.

| Field | Type | Notes |
|-------|------|-------|
| `episode_id` | str | Target episode |
| `action_needed` | bool | True iff the rule's condition holds |
| `reason` | str | e.g. "on Apple Podcasts, no YouTube clip yet" |
| `rule` | str | Rule identifier (`apple_without_youtube`) |

**Rules**: computed purely from `Episode` fields; MUST NOT mutate any `Episode` or external
state. Rule condition: `"apple" in present_on AND "youtube" in missing_from`.

---

## 4. WritebackAttempt (action layer audit record)

One record per writeback attempt, mock or real. Produced by `action/`.

| Field | Type | Notes |
|-------|------|-------|
| `attempt_id` | str | Unique id |
| `episode_id` | str | Episode acted on |
| `mode` | enum(`mock`,`real`) | Mock logs only; real calls the API |
| `target` | str | Always the owned test channel / test video |
| `intended_change` | str | e.g. "append Apple Podcasts link to show notes" |
| `outcome` | enum(`success`,`failure`,`skipped_idempotent`) | Result |
| `error` | str \| null | On failure, for retry context |
| `timestamp` | datetime | When attempted |

**Rules**: every attempt is appended to `run/action/audit.log` (Principle IV). `target` MUST be
the throwaway test channel — never a third party. A retry MUST detect an already-applied change
(`skipped_idempotent`) rather than duplicate it.

---

## Flow (data → logic → action)

```text
YouTube API ─┐                         ┌─ Decision(action_needed?) ─┐
             ├─> RawPlatformRecord ──> Episode ──>                   ├─> WritebackAttempt
Apple API ───┘   (staging)    (resolve+conform)  └─ read-only rule ─┘   (mock → real, logged)
```
