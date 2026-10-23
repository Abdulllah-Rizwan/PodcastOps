"""Apple Podcasts SourceAdapter (read via the public iTunes lookup API; no auth).

Implements the engine `SourceAdapter` port. The iTunes lookup API is public and unauthenticated —
no client id, secret, token, or market/Premium gate. Apple exposes no public listen counts, so no
engagement data is produced. Carried forward from the slice's apple_gateway. Read-only (write=False).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Mapping
from urllib.parse import urlencode

import httpx

from ontology_engine.access.check import AccessCheckResult
from ontology_engine.ingest.adapter import Capabilities, Capability
from ontology_engine.ingest.staging import StagingRecord

SOURCE_KEY = "apple"
OBJECT_TYPE_KEY = "episode"
_LOOKUP_URL = "https://itunes.apple.com/lookup"


def _parse_release_date(value: str) -> str:
    """Apple releaseDate is an ISO-8601 datetime; keep just the date (ISO string)."""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()


def map_episode(ep: dict[str, Any]) -> dict[str, Any]:
    """Map an iTunes `podcastEpisode` result into a normalized staging payload."""
    duration_ms = ep.get("trackTimeMillis")
    duration_seconds = round(duration_ms / 1000) if isinstance(duration_ms, (int, float)) else None
    url = ep.get("trackViewUrl") or ep.get("episodeUrl")
    return {
        "title": ep.get("trackName", ""),
        "description": ep.get("description") or ep.get("shortDescription"),
        "published_at": _parse_release_date(ep.get("releaseDate", "")),
        "duration_seconds": duration_seconds,
        "url": url,
        "_raw": ep,
    }


class AppleAdapter:
    """Engine source adapter over the public iTunes lookup API."""

    source_key = SOURCE_KEY

    def __init__(self, *, country: str = "US", limit: int = 200) -> None:
        self._country = country
        self._limit = limit

    def capabilities(self) -> Capabilities:
        return Capabilities(read=True, write=False)

    def _lookup(self, collection_id: str, *, limit: int) -> list[dict[str, Any]]:
        params = urlencode(
            {
                "id": collection_id,
                "entity": "podcastEpisode",
                "limit": limit,
                "country": self._country,
            }
        )
        resp = httpx.get(f"{_LOOKUP_URL}?{params}", timeout=30)
        resp.raise_for_status()
        return resp.json().get("results", [])

    def read(self, config: Mapping[str, object]) -> Iterable[StagingRecord]:  # pragma: no cover
        collection_id = str(config.get("target") or "")
        if not collection_id:
            return []
        results = self._lookup(collection_id, limit=self._limit)
        # The first result is the show itself; episodes carry wrapperType == "podcastEpisode".
        records: list[StagingRecord] = []
        for ep in results:
            if ep.get("wrapperType") != "podcastEpisode":
                continue
            external_id = str(ep.get("trackId") or ep.get("episodeGuid") or "")
            records.append(
                StagingRecord(
                    source_key=SOURCE_KEY,
                    object_type_key=OBJECT_TYPE_KEY,
                    external_id=external_id,
                    raw_payload=map_episode(ep),
                )
            )
        return records

    def confirm_access(self, capability: Capability) -> AccessCheckResult:  # pragma: no cover
        if capability != "read":
            return AccessCheckResult(
                source_key=SOURCE_KEY,
                capability=capability,
                ok=False,
                detail="apple source is read-only (public iTunes lookup)",
            )
        return AccessCheckResult(
            source_key=SOURCE_KEY,
            capability="read",
            ok=True,
            detail="public iTunes lookup — no auth required",
        )
