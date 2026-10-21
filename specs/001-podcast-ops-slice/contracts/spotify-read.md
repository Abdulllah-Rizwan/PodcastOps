# Contract: Spotify Read (ingest gateway)

**Component**: `src/podcast_ops/ingest/spotify_gateway.py` — Adapter over Spotify Web API.
**Direction**: inbound read, public metadata. **Auth**: Client Credentials flow.

## Interface (internal port)

```
SpotifyGateway.list_episodes(show_id: str) -> list[RawPlatformRecord]
```

## Upstream calls

| Purpose | API call | fields |
|---------|----------|--------|
| Show meta | `GET /v1/shows/{id}` | name, publisher |
| Episodes | `GET /v1/shows/{id}/episodes` (paged, `limit`/`offset`) | name, description, release_date, duration_ms, id, external_urls |

## Produced `RawPlatformRecord` (platform=`spotify`)

- `platform_id` ← episode `id`
- `title` ← episode `name`
- `description` ← episode `description`
- `published_at` ← `release_date` (handle `release_date_precision`)
- `duration_seconds` ← `duration_ms / 1000`
- `engagement` ← `null` (Spotify exposes no public listen counts — consistent with the constitution)
- `raw` ← full episode object

## Contract rules

- Reads only; no write endpoints exist for episode publishing — none are called.
- Handles token acquisition/refresh via Client Credentials; token never logged or committed.
- Paginates through all episodes (`next`).
- MUST surface auth/rate-limit (HTTP 429) errors rather than emit partial records silently.
- Contract test: against a recorded fixture, the mapping holds and `engagement` is `null`.
