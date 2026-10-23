"""T027 (US1) — the baseline matcher is the hard core (Principle III).

It must fuse the same episode across sources despite mismatched IDs and slightly different titles,
and must NOT fuse two genuinely different episodes, nor pair records from the same source. (Subtle
near-duplicates with high title overlap are the motivation for the similarity matcher + evals added
in US3; the baseline is honest about what it can do and exposes signals + confidence either way.)
"""

from __future__ import annotations

from ontology_engine.ingest.staging import StagingRecord
from ontology_engine.resolve.baseline import BaselineMatcher, normalize_title


def _rec(source: str, ext: str, title: str, date: str, dur: int) -> StagingRecord:
    return StagingRecord(
        source_key=source,
        object_type_key="episode",
        external_id=ext,
        raw_payload={"title": title, "published_at": date, "duration_s": dur},
    )


def test_normalize_strips_tags_and_episode_numbers() -> None:
    assert normalize_title("Ep 42: The Brain [FULL]") == "the brain"
    assert normalize_title("The Brain | Full Episode") == "the brain full episode"


def test_fuses_same_episode_across_sources() -> None:
    yt = _rec("youtube", "y1", "Ep 42: The Science of Sleep", "2024-03-01", 3600)
    ap = _rec("apple", "a1", "The Science of Sleep (Full Episode)", "2024-03-01", 3580)
    groups = BaselineMatcher().match([yt, ap])

    fused = [g for g in groups if g.is_fused]
    assert len(fused) == 1
    group = fused[0]
    assert {r.external_id for r in group.members} == {"y1", "a1"}
    assert group.confidence >= 0.70
    # Signals are inspectable (Principle III): title drives it, all three are present.
    names = {s.name for s in group.signals}
    assert names == {"title_similarity", "date_proximity", "duration_proximity"}
    assert next(s for s in group.signals if s.name == "title_similarity").value >= 0.8


def test_does_not_fuse_different_episodes() -> None:
    # Same show, adjacent uploads, genuinely different episodes — must stay separate.
    yt = _rec("youtube", "y1", "Morning Sunlight for Energy", "2024-03-01", 3200)
    ap = _rec("apple", "a1", "Evening Routines for Better Sleep", "2024-03-02", 1100)
    groups = BaselineMatcher().match([yt, ap])

    assert all(not g.is_fused for g in groups)
    assert len(groups) == 2  # two single-source instances
    # A single-source group still records the best rejected candidate (the near-miss).
    singles = {g.members[0].external_id: g for g in groups}
    assert singles["y1"].rejected_best is not None
    assert singles["y1"].rejected_best.external_id == "a1"
    assert singles["y1"].rejected_best.score < 0.70


def test_never_pairs_within_the_same_source() -> None:
    a = _rec("youtube", "y1", "The Science of Sleep", "2024-03-01", 3600)
    b = _rec("youtube", "y2", "The Science of Sleep", "2024-03-01", 3600)
    groups = BaselineMatcher().match([a, b])
    # Identical titles but same source → no fusion (resolution is cross-source).
    assert all(not g.is_fused for g in groups)
    assert len(groups) == 2


def test_one_to_one_no_fan_out() -> None:
    yt = _rec("youtube", "y1", "The Science of Sleep", "2024-03-01", 3600)
    ap1 = _rec("apple", "a1", "The Science of Sleep", "2024-03-01", 3600)
    ap2 = _rec("apple", "a2", "The Science of Sleep", "2024-03-01", 3600)
    groups = BaselineMatcher().match([yt, ap1, ap2])
    fused = [g for g in groups if g.is_fused]
    # y1 matches exactly one apple record; the other stays single (no fan-out).
    assert len(fused) == 1
    assert len(fused[0].members) == 2
    assert sum(1 for g in groups if not g.is_fused) == 1
