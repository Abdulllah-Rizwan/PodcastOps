"""YouTube SourceAdapter (read uploads + public engagement counts; write via videos.update).

Implements the engine `SourceAdapter` port. Mapping (pure, testable) is separated from transport
(live, lazy-imported googleapiclient), carried forward from the slice's youtube_gateway. Reads
yield StagingRecords only — never ObjectInstances (Principle II). Writes target an owned test
channel only and are gated by `confirm_access("write")` (Principles IV/V).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Iterable, Mapping

from ontology_engine.access.check import AccessCheckResult
from ontology_engine.ingest.adapter import Capabilities, Capability
from ontology_engine.ingest.staging import StagingRecord

SOURCE_KEY = "youtube"
OBJECT_TYPE_KEY = "episode"
WRITE_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"

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


def map_video_item(item: dict[str, Any]) -> dict[str, Any]:
    """Map a YouTube `videos.list` item into a normalized staging payload."""
    snippet = item.get("snippet", {})
    content = item.get("contentDetails", {})
    stats = item.get("statistics", {})
    published_raw = snippet.get("publishedAt", "")
    published = datetime.fromisoformat(published_raw.replace("Z", "+00:00")).date()
    return {
        "title": snippet.get("title", ""),
        "description": snippet.get("description"),
        "published_at": published.isoformat(),
        "duration_seconds": parse_iso8601_duration(content.get("duration")),
        "engagement": {
            "views": _to_int(stats.get("viewCount")),
            "likes": _to_int(stats.get("likeCount")),
            "comments": _to_int(stats.get("commentCount")),
        },
        "url": f"https://www.youtube.com/watch?v={item.get('id', '')}",
        "_raw": item,
    }


class YouTubeAdapter:
    """Engine source adapter over the YouTube Data API v3."""

    source_key = SOURCE_KEY

    def __init__(
        self,
        *,
        api_key: str | None = None,
        oauth_token_path: str | None = None,
        test_channel_id: str | None = None,
        test_video_id: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._oauth_token_path = oauth_token_path
        self._test_channel_id = test_channel_id
        self._test_video_id = test_video_id

    def capabilities(self) -> Capabilities:
        return Capabilities(read=True, write=True)

    # --- read (staging only) --------------------------------------------

    @staticmethod
    def _uploads_playlist_id(source: str) -> str:
        # A channel id (UC...) maps to its uploads playlist (UU...). A playlist id is used as-is.
        return "UU" + source[2:] if source.startswith("UC") else source

    def _client(self):  # pragma: no cover - live transport
        from googleapiclient.discovery import build

        return build("youtube", "v3", developerKey=self._api_key, cache_discovery=False)

    def read(self, config: Mapping[str, object]) -> Iterable[StagingRecord]:  # pragma: no cover
        source = str(config.get("target") or "")
        if not source:
            return []
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

        records: list[StagingRecord] = []
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i : i + 50]
            resp = (
                yt.videos()
                .list(part="snippet,contentDetails,statistics", id=",".join(batch))
                .execute()
            )
            for item in resp.get("items", []):
                records.append(
                    StagingRecord(
                        source_key=SOURCE_KEY,
                        object_type_key=OBJECT_TYPE_KEY,
                        external_id=item["id"],
                        raw_payload=map_video_item(item),
                    )
                )
        return records

    # --- access gate (Principle V) --------------------------------------

    def confirm_access(self, capability: Capability) -> AccessCheckResult:  # pragma: no cover
        if capability == "read":
            return self._confirm_read()
        if capability == "write":
            return self._confirm_write()
        return AccessCheckResult(
            source_key=SOURCE_KEY, capability=capability, ok=False, detail="unknown capability"
        )

    def _confirm_read(self) -> AccessCheckResult:  # pragma: no cover - live
        if not self._api_key:
            return AccessCheckResult(
                source_key=SOURCE_KEY, capability="read", ok=False, detail="missing YOUTUBE_API_KEY"
            )
        try:
            self._client().channels().list(part="id", id="UC_x5XG1OV2P6uZZ5FSM9Ttw").execute()
            return AccessCheckResult(source_key=SOURCE_KEY, capability="read", ok=True, detail="ok")
        except Exception as exc:  # noqa: BLE001 - surface any probe failure as not-ok
            return AccessCheckResult(
                source_key=SOURCE_KEY, capability="read", ok=False, detail=f"error: {exc}"
            )

    def _confirm_write(self) -> AccessCheckResult:  # pragma: no cover - live
        if not self._oauth_token_path:
            return AccessCheckResult(
                source_key=SOURCE_KEY,
                capability="write",
                ok=False,
                detail="missing YOUTUBE_OAUTH_TOKEN (run OAuth consent first)",
            )
        if not (self._test_channel_id and self._test_video_id):
            return AccessCheckResult(
                source_key=SOURCE_KEY,
                capability="write",
                ok=False,
                detail="missing TEST_CHANNEL_ID / TEST_VIDEO_ID",
            )
        try:
            from google.oauth2.credentials import Credentials

            creds = Credentials.from_authorized_user_file(self._oauth_token_path)
            if WRITE_SCOPE not in set(creds.scopes or []):
                return AccessCheckResult(
                    source_key=SOURCE_KEY,
                    capability="write",
                    ok=False,
                    detail="token lacks scope youtube.force-ssl",
                )
            return AccessCheckResult(
                source_key=SOURCE_KEY,
                capability="write",
                ok=True,
                detail="ok (write scope present)",
            )
        except Exception as exc:  # noqa: BLE001
            return AccessCheckResult(
                source_key=SOURCE_KEY, capability="write", ok=False, detail=f"error: {exc}"
            )
