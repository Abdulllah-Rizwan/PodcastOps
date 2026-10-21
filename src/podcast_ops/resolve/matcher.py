"""Entity resolution — the hard core of the project (Principle III).

Matches the same real-world episode across YouTube and Spotify despite mismatched IDs, titles
and schemas. Uses a multi-signal, inspectable strategy: normalize titles, block by release-date
proximity, score by weighted (title similarity + date closeness + duration closeness), then take
one-to-one matches above a threshold. No exact-equality shortcut; no fan-out; no false merge.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from podcast_ops.ingest.records import RawPlatformRecord

# Tokens commonly differing across platforms that should not drive (non-)matches.
_EPISODE_NUM = re.compile(r"\b(?:ep|episode|pt|part|#)\s*\.?\s*\d+\b", re.IGNORECASE)
_BRACKETED = re.compile(r"[\(\[\{].*?[\)\]\}]")
_NON_ALNUM = re.compile(r"[^a-z0-9\s]")
_WS = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    """Lowercase; strip bracketed tags, episode-number tokens, punctuation, extra whitespace."""
    t = title.lower()
    t = _BRACKETED.sub(" ", t)
    t = _EPISODE_NUM.sub(" ", t)
    t = _NON_ALNUM.sub(" ", t)
    t = _WS.sub(" ", t).strip()
    return t


@dataclass(frozen=True)
class MatchConfig:
    date_block_days: int = 3
    title_weight: float = 0.6
    date_weight: float = 0.25
    duration_weight: float = 0.15
    threshold: float = 0.70


@dataclass(frozen=True)
class Match:
    youtube_index: int
    spotify_index: int
    score: float


def _date_score(a: RawPlatformRecord, b: RawPlatformRecord) -> float:
    delta = abs((a.published_at - b.published_at).days)
    # 1.0 at same day, decaying to 0 at 14 days apart.
    return max(0.0, 1.0 - delta / 14.0)


def _duration_score(a: RawPlatformRecord, b: RawPlatformRecord) -> float:
    if a.duration_seconds is None or b.duration_seconds is None:
        return 0.5  # unknown: neutral, neither rewarded nor penalised
    longer = max(a.duration_seconds, b.duration_seconds, 1)
    diff = abs(a.duration_seconds - b.duration_seconds)
    return max(0.0, 1.0 - diff / longer)


def _title_score(a: RawPlatformRecord, b: RawPlatformRecord) -> float:
    return fuzz.token_sort_ratio(normalize_title(a.title), normalize_title(b.title)) / 100.0


class Matcher:
    """Strategy that pairs YouTube and Spotify records into episode matches."""

    def __init__(self, config: MatchConfig | None = None) -> None:
        self.config = config or MatchConfig()

    def score(self, yt: RawPlatformRecord, sp: RawPlatformRecord) -> float:
        c = self.config
        return (
            c.title_weight * _title_score(yt, sp)
            + c.date_weight * _date_score(yt, sp)
            + c.duration_weight * _duration_score(yt, sp)
        )

    def match(
        self,
        youtube: list[RawPlatformRecord],
        spotify: list[RawPlatformRecord],
    ) -> list[Match]:
        """Return one-to-one matches above threshold, greedily by descending score."""
        c = self.config
        candidates: list[Match] = []
        for i, yt in enumerate(youtube):
            for j, sp in enumerate(spotify):
                # Blocking: skip pairs far apart in release date.
                if abs((yt.published_at - sp.published_at).days) > c.date_block_days:
                    continue
                s = self.score(yt, sp)
                if s >= c.threshold:
                    candidates.append(Match(i, j, s))

        candidates.sort(key=lambda m: m.score, reverse=True)
        used_yt: set[int] = set()
        used_sp: set[int] = set()
        result: list[Match] = []
        for m in candidates:
            if m.youtube_index in used_yt or m.spotify_index in used_sp:
                continue  # enforce one-to-one — no fan-out, no false merge
            used_yt.add(m.youtube_index)
            used_sp.add(m.spotify_index)
            result.append(m)
        return result
