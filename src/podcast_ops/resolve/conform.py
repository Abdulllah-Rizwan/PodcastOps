"""Conform step: build Episode objects from matched pairs and one-sided records.

Takes the raw staged records plus the matcher's output and produces the clean, fused object
layer. This is where raw finally becomes an object (Principle II).
"""

from __future__ import annotations

import hashlib

from podcast_ops.ingest.records import Platform, RawPlatformRecord
from podcast_ops.objects.episode import ALL_PLATFORMS, Episode, PlatformRef
from podcast_ops.resolve.matcher import Match, Matcher, normalize_title

_YT_URL = "https://www.youtube.com/watch?v={id}"


def _youtube_ref(r: RawPlatformRecord) -> PlatformRef:
    return PlatformRef(
        platform="youtube",
        platform_id=r.platform_id,
        url=_YT_URL.format(id=r.platform_id),
        title=r.title,
        engagement=r.engagement,
    )


def _spotify_ref(r: RawPlatformRecord) -> PlatformRef:
    url = (r.raw or {}).get("_url") or (r.raw.get("external_urls", {}) or {}).get("spotify")
    return PlatformRef(
        platform="spotify",
        platform_id=r.platform_id,
        url=url,
        title=r.title,
        engagement=None,
    )


def _episode_id(*records: RawPlatformRecord) -> str:
    """Stable id from normalized title + ISO date of the first available record."""
    base = records[0]
    key = f"{normalize_title(base.title)}|{base.published_at.isoformat()}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _missing(present: set[Platform]) -> list[Platform]:
    return sorted(ALL_PLATFORMS - present)


def conform(
    youtube: list[RawPlatformRecord],
    spotify: list[RawPlatformRecord],
    matches: list[Match] | None = None,
    matcher: Matcher | None = None,
) -> list[Episode]:
    """Fuse staged records into Episode objects."""
    if matches is None:
        matcher = matcher or Matcher()
        matches = matcher.match(youtube, spotify)

    episodes: list[Episode] = []
    matched_yt: set[int] = set()
    matched_sp: set[int] = set()

    # Two-sided episodes.
    for m in matches:
        yt = youtube[m.youtube_index]
        sp = spotify[m.spotify_index]
        matched_yt.add(m.youtube_index)
        matched_sp.add(m.spotify_index)
        episodes.append(
            Episode(
                episode_id=_episode_id(yt, sp),
                title=yt.title,
                published_at=yt.published_at,
                duration_seconds=yt.duration_seconds or sp.duration_seconds,
                youtube=_youtube_ref(yt),
                spotify=_spotify_ref(sp),
                present_on=["youtube", "spotify"],
                missing_from=[],
                match_confidence=round(m.score, 4),
            )
        )

    # One-sided: YouTube only.
    for i, yt in enumerate(youtube):
        if i in matched_yt:
            continue
        episodes.append(
            Episode(
                episode_id=_episode_id(yt),
                title=yt.title,
                published_at=yt.published_at,
                duration_seconds=yt.duration_seconds,
                youtube=_youtube_ref(yt),
                spotify=None,
                present_on=["youtube"],
                missing_from=_missing({"youtube"}),
                match_confidence=None,
            )
        )

    # One-sided: Spotify only.
    for j, sp in enumerate(spotify):
        if j in matched_sp:
            continue
        episodes.append(
            Episode(
                episode_id=_episode_id(sp),
                title=sp.title,
                published_at=sp.published_at,
                duration_seconds=sp.duration_seconds,
                youtube=None,
                spotify=_spotify_ref(sp),
                present_on=["spotify"],
                missing_from=_missing({"spotify"}),
                match_confidence=None,
            )
        )

    return episodes
