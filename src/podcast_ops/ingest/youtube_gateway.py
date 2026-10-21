"""YouTube read gateway (Adapter over YouTube Data API v3).

Mapping (pure, contract-tested) is separated from transport (live, lazy-imported) so the
mapping can be verified against recorded fixtures without network or SDK (Principle VI).
Reads only — never calls a write endpoint (see contracts/youtube-read.md).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from podcast_ops.ingest.records import Engagement, RawPlatformRecord

_ISO_DURATION = re.compile(
    r"P(?:(?P<days>\d+)D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?"
)


def parse_iso8601_duration(value: str | None) -> int | None:
    """Parse an ISO-8601 duration (e.g. 'PT1H2M3S') into whole seconds."""
    if not value:
        return None
    m = _ISO_DURATION.fullmatch(value)
    if not m:
        return None
    parts = {k: int(v) if v else 0 for k, v in m.groupdict().items()}
    return parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def map_video_item(item: dict[str, Any]) -> RawPlatformRecord:
    """Map a YouTube `videos.list` item to a RawPlatformRecord."""
    snippet = item.get("snippet", {})
    content = item.get("contentDetails", {})
    stats = item.get("statistics", {})
    published_raw = snippet.get("publishedAt", "")
    published = datetime.fromisoformat(published_raw.replace("Z", "+00:00")).date()

    engagement = Engagement(
        views=_to_int(stats.get("viewCount")),
        likes=_to_int(stats.get("likeCount")),
        comments=_to_int(stats.get("commentCount")),
    )

    return RawPlatformRecord(
        platform="youtube",
        platform_id=item["id"],
        title=snippet.get("title", ""),
        description=snippet.get("description"),
        published_at=published,
        duration_seconds=parse_iso8601_duration(content.get("duration")),
        engagement=engagement,
        raw=item,
    )


class YouTubeGateway:
    """Live transport over the YouTube Data API v3 (reads via API key)."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("YouTube API key is required")
        self._api_key = api_key

    def _client(self):  # pragma: no cover - thin wrapper over the SDK
        from googleapiclient.discovery import build  # lazy import

        return build("youtube", "v3", developerKey=self._api_key, cache_discovery=False)

    @staticmethod
    def _uploads_playlist_id(source: str) -> str:
        # A channel id (UC...) maps to its uploads playlist (UU...). A playlist id is used as-is.
        if source.startswith("UC"):
            return "UU" + source[2:]
        return source

    def list_episodes(self, source: str) -> list[RawPlatformRecord]:  # pragma: no cover
        """Enumerate the show's videos and hydrate them into RawPlatformRecords (live)."""
        yt = self._client()
        playlist_id = self._uploads_playlist_id(source)

        video_ids: list[str] = []
        page_token: str | None = None
        while True:
            resp = (
                yt.playlistItems()
                .list(
                    part="contentDetails",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=page_token,
                )
                .execute()
            )
            for it in resp.get("items", []):
                vid = it.get("contentDetails", {}).get("videoId")
                if vid:
                    video_ids.append(vid)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        records: list[RawPlatformRecord] = []
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i : i + 50]
            resp = (
                yt.videos()
                .list(part="snippet,contentDetails,statistics", id=",".join(batch))
                .execute()
            )
            records.extend(map_video_item(item) for item in resp.get("items", []))
        return records
