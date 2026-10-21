"""Spotify read gateway (Adapter over the Spotify Web API).

Mapping (pure, contract-tested) is separated from transport (live). Client-Credentials flow;
reads public catalog metadata only (see contracts/spotify-read.md). Spotify exposes no public
listen counts, so `engagement` is always None.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import httpx

from podcast_ops.ingest.records import RawPlatformRecord

_TOKEN_URL = "https://accounts.spotify.com/api/token"
_API_BASE = "https://api.spotify.com/v1"


def _parse_release_date(value: str, precision: str | None) -> date:
    """Spotify release_date may be year / year-month / year-month-day."""
    if precision == "year" or len(value) == 4:
        return date(int(value), 1, 1)
    if precision == "month" or len(value) == 7:
        y, m = value.split("-")[:2]
        return date(int(y), int(m), 1)
    return datetime.fromisoformat(value).date()


def map_episode(ep: dict[str, Any]) -> RawPlatformRecord:
    """Map a Spotify show-episode object to a RawPlatformRecord."""
    duration_ms = ep.get("duration_ms")
    duration_seconds = round(duration_ms / 1000) if isinstance(duration_ms, (int, float)) else None
    url = (ep.get("external_urls") or {}).get("spotify")

    record_raw = dict(ep)
    if url:
        record_raw.setdefault("_url", url)

    return RawPlatformRecord(
        platform="spotify",
        platform_id=ep["id"],
        title=ep.get("name", ""),
        description=ep.get("description"),
        published_at=_parse_release_date(
            ep.get("release_date", ""), ep.get("release_date_precision")
        ),
        duration_seconds=duration_seconds,
        engagement=None,  # Spotify exposes no public listen counts
        raw=record_raw,
    )


class SpotifyGateway:
    """Live transport over the Spotify Web API (Client-Credentials flow)."""

    def __init__(self, client_id: str, client_secret: str) -> None:
        if not client_id or not client_secret:
            raise ValueError("Spotify client id and secret are required")
        self._client_id = client_id
        self._client_secret = client_secret

    def _token(self) -> str:  # pragma: no cover - requires network
        resp = httpx.post(
            _TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self._client_id, self._client_secret),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def list_episodes(self, show_id: str) -> list[RawPlatformRecord]:  # pragma: no cover
        token = self._token()
        headers = {"Authorization": f"Bearer {token}"}
        records: list[RawPlatformRecord] = []
        url: str | None = f"{_API_BASE}/shows/{show_id}/episodes?limit=50"
        with httpx.Client(headers=headers, timeout=30) as client:
            while url:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
                for ep in data.get("items", []):
                    if ep:
                        records.append(map_episode(ep))
                url = data.get("next")
        return records
