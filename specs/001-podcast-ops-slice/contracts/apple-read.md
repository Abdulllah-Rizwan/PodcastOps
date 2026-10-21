# Contract: Apple Podcasts Read (ingest gateway)

**Component**: `src/podcast_ops/ingest/apple_gateway.py` — Adapter over the public iTunes
lookup API.
**Direction**: inbound read, public metadata. **Auth**: none (public, unauthenticated).

## Interface (internal port)

```
AppleGateway.list_episodes(collection_id: str) -> list[RawPlatformRecord]
```

## Upstream calls

| Purpose | API call | fields |
|---------|----------|--------|
| Episodes | `GET https://itunes.apple.com/lookup?id={collectionId}&entity=podcastEpisode&limit=200&country=US` | trackId, trackName, description, releaseDate, trackTimeMillis, trackViewUrl, wrapperType |

The lookup response's first result is the show itself; episode items carry
`wrapperType == "podcastEpisode"` and are the only ones mapped.

## Produced `RawPlatformRecord` (platform=`apple`)

- `platform_id` ← `trackId` (stringified; falls back to `episodeGuid`)
- `title` ← `trackName`
- `description` ← `description` (or `shortDescription`)
- `published_at` ← `releaseDate` (ISO-8601 datetime, e.g. `2024-03-01T10:00:00Z` → date)
- `duration_seconds` ← `trackTimeMillis / 1000` (rounded; `null` if absent)
- `engagement` ← `null` (Apple exposes no public listen counts — consistent with the constitution)
- `raw` ← full episode object (plus `_url` convenience from `trackViewUrl`)

## Contract rules

- Reads only; no write endpoints exist and none are called.
- No credentials, token, market, or subscription required (this is why Apple replaced Spotify —
  see `decisions.md`, 2026-10-21).
- Returns only `wrapperType == "podcastEpisode"` items; the show header is skipped.
- MUST surface HTTP/transport errors rather than emit partial records silently.
- Contract test: against a recorded fixture, the mapping holds and `engagement` is `null`.
