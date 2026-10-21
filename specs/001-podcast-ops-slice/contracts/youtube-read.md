# Contract: YouTube Read (ingest gateway)

**Component**: `src/podcast_ops/ingest/youtube_gateway.py` — Adapter over YouTube Data API v3.
**Direction**: inbound read, public metadata. **Auth**: API key (no OAuth for reads).

## Interface (internal port)

```
YouTubeGateway.list_episodes(channel_or_playlist_id: str) -> list[RawPlatformRecord]
```

## Upstream calls

| Purpose | API call | part / fields | quota |
|---------|----------|---------------|-------|
| Enumerate uploads | `playlistItems.list` (uploads playlist) or `search.list` | `snippet` | 1 / 100 |
| Hydrate details | `videos.list` | `snippet,contentDetails,statistics` | 1 |

## Produced `RawPlatformRecord` (platform=`youtube`)

- `platform_id` ← `videoId`
- `title` ← `snippet.title`
- `description` ← `snippet.description`
- `published_at` ← `snippet.publishedAt` (date)
- `duration_seconds` ← parse `contentDetails.duration` (ISO 8601)
- `engagement` ← `{views: statistics.viewCount, likes: statistics.likeCount, comments: statistics.commentCount}`
- `raw` ← full `videos.list` item

## Contract rules

- Reads only; MUST NOT call any write endpoint.
- MUST surface API errors / quota exhaustion (do not emit partial records as if complete).
- Paginates via `nextPageToken` until the channel's videos are exhausted.
- Contract test: against a recorded fixture, the mapping above holds and engagement counts are integers.
