"""T045 — the ER eval harness: correct precision/recall/F1, and regression detection.

Uses a tiny, controlled fixture (not the full golden set) so the assertions are exact. The full
multi-signal baseline separates the hard negatives (title-similar but date-far); a deliberately
*weakened* title-only matcher accepts them — the harness reports the precision drop and the gate
fails, which is exactly how CI catches a resolution regression (SC-007).
"""

from __future__ import annotations

from rapidfuzz import fuzz

from ontology_engine.evals.golden import GoldenCase, GoldenRecord
from ontology_engine.evals.resolution import EvalThresholds, evaluate
from ontology_engine.ingest.staging import StagingRecord
from ontology_engine.resolve.baseline import BaselineMatcher, normalize_title
from ontology_engine.resolve.decision import Signal


def _case(cid, kind, lt, ld, ls, rt, rd, rs) -> GoldenCase:
    return GoldenCase(
        case_id=cid,
        kind=kind,
        left=GoldenRecord(
            source_key="youtube",
            external_id=f"{cid}-y",
            payload={"title": lt, "published_at": ld, "duration_s": ls},
        ),
        right=GoldenRecord(
            source_key="apple",
            external_id=f"{cid}-a",
            payload={"title": rt, "published_at": rd, "duration_s": rs},
        ),
    )


def _fixture() -> list[GoldenCase]:
    cases: list[GoldenCase] = []
    # 3 true matches: identical title + date.
    for i, (title, d, s) in enumerate(
        [
            ("The Science of Sleep", "2024-01-10", 3600),
            ("Focus and Dopamine", "2024-02-10", 3200),
            ("Cold Exposure Protocols", "2024-03-10", 4100),
        ]
    ):
        cases.append(_case(f"m{i}", "match", title, d, s, title, d, s))
    # 3 hard negatives: title-similar but ~5 months apart (date-far) with equal duration.
    for i, (lt, rt) in enumerate(
        [
            ("The Science of Sleep and Naps", "The Science of Sleep"),
            ("Focus and Dopamine Explained", "Focus and Dopamine"),
            ("Cold Exposure Protocols Deep Dive", "Cold Exposure Protocols"),
        ]
    ):
        cases.append(_case(f"n{i}", "non_match", lt, "2024-01-10", 3600, rt, "2024-06-10", 3600))
    return cases


class TitleOnlyMatcher:
    """A deliberately weakened matcher: title similarity alone, ignoring date/duration."""

    matcher_kind = "title_only"

    class _Cfg:
        threshold = 0.70

    config = _Cfg()

    def score(self, a: StagingRecord, b: StagingRecord) -> tuple[list[Signal], float]:
        r = (
            fuzz.token_sort_ratio(
                normalize_title(str(a.raw_payload.get("title", ""))),
                normalize_title(str(b.raw_payload.get("title", ""))),
            )
            / 100.0
        )
        return [Signal(name="title_only", value=r, weight=1.0, contribution=r)], round(r, 4)


def test_fixture_is_adversarial_for_baseline():
    # Sanity: the full baseline keeps every hard negative below its threshold.
    matcher = BaselineMatcher()
    for case in _fixture():
        if case.kind == "non_match":
            _, conf = matcher.score(
                case.left.as_staging("episode"), case.right.as_staging("episode")
            )
            assert conf < matcher.config.threshold


def test_baseline_scores_perfectly_and_passes_gate():
    result = evaluate(BaselineMatcher(), _fixture())
    assert (result.true_positives, result.false_positives) == (3, 0)
    assert (result.false_negatives, result.true_negatives) == (0, 3)
    assert result.precision == 1.0 and result.recall == 1.0 and result.f1 == 1.0
    passed, reasons = result.gate()
    assert passed and reasons == []


def test_weakened_matcher_is_detected_as_regression():
    result = evaluate(TitleOnlyMatcher(), _fixture())
    # Title-only accepts the title-similar negatives → false positives → precision drops.
    assert result.false_positives >= 2
    assert result.precision < 0.95
    passed, reasons = result.gate(EvalThresholds())
    assert not passed
    assert any("precision" in r for r in reasons)
