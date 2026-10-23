"""BaselineMatcher — the deterministic entity-resolution strategy (Principle III).

Matches the same real-world thing across sources despite mismatched IDs, titles, and schemas, using
an inspectable, multi-signal score (normalized title similarity + release-date proximity + duration
proximity via rapidfuzz). It generates candidates (`block`), scores each (`score`), then greedily
assigns one-to-one matches above a threshold (`match`). No exact-string shortcut; no fan-out; no
false merge. A deterministic baseline is retained even once a similarity matcher is added, so the
upgrade can be measured against it (Principle III).

The matcher is domain-agnostic: it compares named fields (configurable) in each staging record's
normalized payload, so any vertical whose adapters normalize to those field names can reuse it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from rapidfuzz import fuzz

from ontology_engine.ingest.staging import StagingRecord
from ontology_engine.resolve.decision import RejectedCandidate, Signal

# Tokens commonly differing across platforms that should not drive (non-)matches.
_EPISODE_NUM = re.compile(r"\b(?:ep|episode|pt|part|#)\s*\.?\s*\d+\b", re.IGNORECASE)
_BRACKETED = re.compile(r"[\(\[\{].*?[\)\]\}]")
_NON_ALNUM = re.compile(r"[^a-z0-9\s]")
_WS = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    """Lowercase; strip bracketed tags, episode-number tokens, punctuation, extra whitespace."""
    t = (title or "").lower()
    t = _BRACKETED.sub(" ", t)
    t = _EPISODE_NUM.sub(" ", t)
    t = _NON_ALNUM.sub(" ", t)
    t = _WS.sub(" ", t).strip()
    return t


@dataclass(frozen=True)
class MatchConfig:
    """Which normalized payload fields to compare, their weights, and the match threshold."""

    title_field: str = "title"
    date_field: str = "published_at"
    duration_field: str = "duration_s"
    date_block_days: int = 3
    title_weight: float = 0.6
    date_weight: float = 0.25
    duration_weight: float = 0.15
    threshold: float = 0.70


@dataclass
class MatchGroup:
    """A resolved group of 1–2 staging records and the signals behind the decision."""

    members: list[StagingRecord]
    signals: list[Signal] = field(default_factory=list)
    confidence: float = 0.0
    rejected_best: RejectedCandidate | None = None

    @property
    def is_fused(self) -> bool:
        return len({r.source_key for r in self.members}) >= 2


def _parse_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


class BaselineMatcher:
    """Deterministic, inspectable matcher over normalized staging payloads."""

    matcher_kind = "baseline"

    def __init__(self, config: MatchConfig | None = None) -> None:
        self.config = config or MatchConfig()

    # --- candidate generation -------------------------------------------

    def block(self, records: list[StagingRecord]) -> list[tuple[StagingRecord, StagingRecord]]:
        """Cross-source pairs within the release-date window (cheap candidate generation)."""
        by_source: dict[str, list[StagingRecord]] = {}
        for r in records:
            by_source.setdefault(r.source_key, []).append(r)

        sources = list(by_source)
        candidates: list[tuple[StagingRecord, StagingRecord]] = []
        for i, sa in enumerate(sources):
            for sb in sources[i + 1 :]:
                for a in by_source[sa]:
                    for b in by_source[sb]:
                        if self._within_date_block(a, b):
                            candidates.append((a, b))
        return candidates

    def _within_date_block(self, a: StagingRecord, b: StagingRecord) -> bool:
        da = _parse_date(a.raw_payload.get(self.config.date_field))
        db = _parse_date(b.raw_payload.get(self.config.date_field))
        if da is None or db is None:
            return True  # cannot block on missing dates; let scoring decide
        return abs((da - db).days) <= self.config.date_block_days

    # --- scoring --------------------------------------------------------

    def score(self, a: StagingRecord, b: StagingRecord) -> tuple[list[Signal], float]:
        c = self.config
        title = self._title_score(a, b)
        dt = self._date_score(a, b)
        dur = self._duration_score(a, b)
        signals = [
            _signal("title_similarity", title, c.title_weight),
            _signal("date_proximity", dt, c.date_weight),
            _signal("duration_proximity", dur, c.duration_weight),
        ]
        confidence = sum(s.contribution for s in signals)
        return signals, round(confidence, 4)

    def _title_score(self, a: StagingRecord, b: StagingRecord) -> float:
        ta = normalize_title(str(a.raw_payload.get(self.config.title_field, "")))
        tb = normalize_title(str(b.raw_payload.get(self.config.title_field, "")))
        return fuzz.token_sort_ratio(ta, tb) / 100.0

    def _date_score(self, a: StagingRecord, b: StagingRecord) -> float:
        da = _parse_date(a.raw_payload.get(self.config.date_field))
        db = _parse_date(b.raw_payload.get(self.config.date_field))
        if da is None or db is None:
            return 0.5  # unknown: neutral
        delta = abs((da - db).days)
        return max(0.0, 1.0 - delta / 14.0)  # 1.0 same day, 0 at 14 days apart

    def _duration_score(self, a: StagingRecord, b: StagingRecord) -> float:
        va = a.raw_payload.get(self.config.duration_field)
        vb = b.raw_payload.get(self.config.duration_field)
        if not isinstance(va, (int, float)) or not isinstance(vb, (int, float)):
            return 0.5  # unknown: neutral
        longer = max(va, vb, 1)
        return max(0.0, 1.0 - abs(va - vb) / longer)

    # --- assignment -----------------------------------------------------

    def match(self, records: list[StagingRecord]) -> list[MatchGroup]:
        """Greedy one-to-one matching above threshold; leftovers become single-source groups."""
        scored: list[tuple[float, StagingRecord, StagingRecord, list[Signal]]] = []
        for a, b in self.block(records):
            signals, conf = self.score(a, b)
            scored.append((conf, a, b, signals))
        scored.sort(key=lambda t: t[0], reverse=True)

        # Track each record's best candidate (regardless of threshold) for the rejected-best note.
        best: dict[str, tuple[float, StagingRecord]] = {}
        for conf, a, b, _ in scored:
            if conf > best.get(a.id, (-1.0, a))[0]:
                best[a.id] = (conf, b)
            if conf > best.get(b.id, (-1.0, b))[0]:
                best[b.id] = (conf, a)

        used: set[str] = set()
        groups: list[MatchGroup] = []
        for conf, a, b, signals in scored:
            if conf < self.config.threshold or a.id in used or b.id in used:
                continue
            used.update({a.id, b.id})
            groups.append(
                MatchGroup(members=[a, b], signals=signals, confidence=conf, rejected_best=None)
            )

        for r in records:
            if r.id in used:
                continue
            rejected = None
            if r.id in best:
                score, other = best[r.id]
                rejected = RejectedCandidate(
                    external_id=other.external_id, source_key=other.source_key, score=score
                )
            groups.append(
                MatchGroup(members=[r], signals=[], confidence=0.0, rejected_best=rejected)
            )
        return groups


def _signal(name: str, value: float, weight: float) -> Signal:
    return Signal(
        name=name, value=round(value, 4), weight=weight, contribution=round(weight * value, 4)
    )
