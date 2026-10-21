# Phase 0 Research: Podcast Ops-Hub Validation Slice

This resolves the open technical choices and, per **Principle V (Confirm API Access Before
Modeling)**, documents the expected API capabilities for the one read and the one write. Each
access finding carries a **verify-at-M0** note: these are to be confirmed live against the
platforms before `data-model.md` is acted on in code.

---

## Decision 1 — Language & stack

- **Decision**: Python 3.11+, with `google-api-python-client` (YouTube), `spotipy`/`httpx`
  (Spotify), `pydantic` v2 (modeling), `rapidfuzz` (matching), `pytest` (tests).
- **Rationale**: Both platforms have mature, well-documented Python clients; `pydantic` gives
  clean typed objects for the staging→object boundary; `rapidfuzz` provides fast, inspectable
  string similarity for honest entity resolution. Lowest friction for a run-once slice.
- **Alternatives considered**: Node/TypeScript (equally viable; Python chosen for terser data
  modeling and `rapidfuzz`); a database for storage (rejected — JSON files are enough for one
  show run once, per Ship-Not-Learn).

## Decision 2 — Storage: local JSON files

- **Decision**: Raw records in `./run/staging/{platform}/*.json`; fused objects in
  `./run/objects/episodes.json`; audit log in `./run/action/audit.log`.
- **Rationale**: Keeps raw and object layers physically separate (Principle II), is trivially
  inspectable for the entity-resolution proof, and needs no infrastructure.
- **Alternatives considered**: SQLite (unneeded complexity for one run); in-memory only
  (rejected — persisting staging vs. objects is part of what the slice demonstrates).

## Decision 3 — YouTube read access *(verify-at-M0)*

- **Decision**: Use **YouTube Data API v3** to read the show's uploads: `search`/`playlistItems`
  to enumerate the channel's videos, and `videos.list` with `part=snippet,statistics` for title,
  publish date, duration (`contentDetails`), and **public engagement counts** (views, likes,
  comments) in `statistics`.
- **Access**: Public reads work with an **API key** (no OAuth). Default quota 10,000 units/day;
  `search.list` costs 100 units/call, `videos.list` 1 unit — enough for one show.
- **Rationale**: Covers all read fields the slice needs, including the public engagement counts
  the spec calls out, with no ownership required.
- **verify-at-M0**: Confirm the API key is enabled for YouTube Data API v3 and that the chosen
  show's channel is enumerable within quota.

## Decision 4 — Spotify read access *(verify-at-M0)*

- **Decision**: Use the **Spotify Web API** with the **Client Credentials** flow to read the
  show and its episodes: `GET /shows/{id}` and `GET /shows/{id}/episodes` for episode name,
  description, release date, and duration.
- **Access**: Client Credentials (app client id/secret) is sufficient for public catalog
  metadata; no user login needed. Note Spotify exposes **no public listen counts** — consistent
  with the constitution's "no owner-only data."
- **Rationale**: Provides the matching signals (title, release date, duration) needed to fuse
  against YouTube; read-only and ownership-free.
- **verify-at-M0**: Confirm app credentials return the show and a full episode page; confirm a
  market param is not required for the chosen show.

## Decision 5 — The one writeback & its target *(verify-at-M0)*

- **Decision**: The writeback is **`videos.update` on a video we own on our throwaway YouTube
  test channel** — updating its description ("show notes") to record the linked Spotify episode.
  Spotify is **not** a writeback target: the Spotify Web API does not permit publishing/editing
  podcast episodes, so attempting it would violate Principle V. YouTube is the write side.
- **Access**: `videos.update` requires **OAuth 2.0** with scope
  `https://www.googleapis.com/auth/youtube.force-ssl`, authorized as the owner of the test
  channel. Cost 50 units.
- **Rationale**: This is the one writeback the platforms actually permit against a channel we
  own, keeping the action safe, reversible, and test-channel-only.
- **verify-at-M0**: Confirm OAuth consent on the test-channel Google account yields a token with
  the write scope and that a `videos.update` on an owned test video succeeds.

## Decision 6 — The one decision rule

- **Decision**: Rule = **"episode exists on Spotify but has no corresponding YouTube clip yet."**
  Pure function over `Episode` objects; returns the subset needing action. Read-only.
- **Rationale**: Directly exercises the fused object (needs both-platform presence data), is the
  example named in the constitution/spec, and pairs naturally with the YouTube writeback.
- **Alternatives considered**: "YouTube video missing show notes" (also valid; the Spotify-only
  rule better showcases cross-platform fusion).

## Decision 7 — Entity-resolution strategy (the hard core)

- **Decision**: Multi-signal matcher behind a `Matcher` Strategy interface:
  1. **Normalize** titles (lowercase, strip sponsor/prefix tags, episode-number tokens,
     punctuation, whitespace).
  2. **Block** candidates by release date proximity (±N days) to cut the comparison space.
  3. **Score** each cross-platform candidate pair by weighted signals: normalized-title
     similarity (`rapidfuzz`), release-date closeness, and duration closeness.
  4. **Match** above a tuned threshold; enforce one-to-one (no fan-out, no false merge);
     unmatched items become one-sided `Episode` objects recording the missing platform.
- **Rationale**: Honest resolution against realistic title/ID/schema mismatches — not exact
  equality. Inspectable scores make matches defensible (Principle III).
- **Alternatives considered**: Exact title match (rejected — fails on real mismatches); fuzzy
  title only (rejected — needs date/duration to avoid merging similarly-titled episodes).

## Decision 8 — Writeback seam & safety

- **Decision**: `WritebackPort` interface with `MockWriteback` (logs `"would publish X to Y"`,
  no external call) and `YouTubeWriteback` (real `videos.update`). CLI `--mock` (default) vs.
  `--real`. Safety: idempotency check (skip if the show-notes marker is already present) so a
  retry after a timeout does not duplicate; every attempt written to the audit log.
- **Rationale**: Satisfies Principle IV (mock-first, safe/retryable, logged) and Principle VI
  (dependency inversion, mockable boundary).

---

## M0 verification checklist (gate before modeling in code)

- [ ] YouTube Data API v3 enabled; API key reads the chosen show within quota.
- [ ] Spotify app credentials read the chosen show + episodes.
- [ ] Chosen show confirmed present on both platforms with enough episodes to demonstrate matching.
- [ ] Test-channel OAuth token obtained with `youtube.force-ssl`; `videos.update` on an owned test video succeeds.
- [ ] Confirmed Spotify permits no episode writeback (so YouTube is the sole write side).

All **NEEDS CLARIFICATION** items from Technical Context are resolved above. The only residual
is the **live confirmation** that M0 performs; the plan deliberately gates coded modeling on it.
