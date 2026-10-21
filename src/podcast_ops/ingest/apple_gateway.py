"""Apple Podcasts read gateway (Adapter over the public iTunes lookup API).

Mapping (pure, contract-tested) is separated from transport (live). The iTunes lookup API is
public and unauthenticated - no client id, secret, token, or market/Premium gate (see
contracts/apple-read.md). Apple exposes no public listen counts, so `engagement` is always None.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from podcast_ops.ingest.records import RawPlatformRecord

_LOOKUP_URL = "https://itunes.apple.com/lookup"


def _parse_release_date(value: str) -> date:
    """Apple releaseDate is ISO-8601 datetime, e.g. '2024-03-01T10:00:00Z'."""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def map_episode(ep: dict[str, Any]) -> RawPlatformRecord:
    """Map an iTunes `podcastEpisode` result object to a RawPlatformRecord."""
    duration_ms = ep.get("trackTimeMillis")
    duration_seconds = round(duration_ms / 1000) if isinstance(duration_ms, (int, float)) else None
    url = ep.get("trackViewUrl") or ep.get("episodeUrl")

    record_raw = dict(ep)
    if url:
        record_raw.setdefault("_url", url)

    return RawPlatformRecord(
        platform="apple",
        platform_id=str(ep.get("trackId") or ep.get("episodeGuid") or ""),
        title=ep.get("trackName", ""),
        description=ep.get("description") or ep.get("shortDescription"),
        published_at=_parse_release_date(ep.get("releaseDate", "")),
        duration_seconds=duration_seconds,
        engagement=None,  # Apple exposes no public listen counts
        raw=record_raw,
    )


class AppleGateway:
    """Live transport over the public iTunes lookup API (no authentication)."""

    def __init__(self, *, country: str = "US", limit: int = 200) -> None:
        self._country = country
        self._limit = limit

    def list_episodes(self, collection_id: str) -> list[RawPlatformRecord]:  # pragma: no cover
        params = urlencode(
            {
                "id": collection_id,
                "entity": "podcastEpisode",
                "limit": self._limit,
                "country": self._country,
            }
        )
        resp = httpx.get(f"{_LOOKUP_URL}?{params}", timeout=30)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        # The first result is the show itself; episodes carry wrapperType == "podcastEpisode".
        return [map_episode(e) for e in results if e.get("wrapperType") == "podcastEpisode"]
