"""The entity-resolution eval harness (Principle III, VI).

Scores every `GoldenCase` with a matcher, compares the prediction (confidence ≥ threshold) to the
label, and reports precision / recall / F1 plus the list of mismatched cases. Fully hermetic: it runs
on in-memory golden data and any `score(a, b)`-shaped matcher — the `BaselineMatcher` needs no
embeddings at all, and `HashingEmbeddings` keeps the similarity/combined matchers offline too.

The `gate()` helper enforces the CI bar (SC-002/SC-007): precision ≥ 95%, recall ≥ 90%. Weakening a
matcher (dropping a signal, lowering a weight) shows up here as a precision/recall drop, failing CI.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from ontology_engine.evals.golden import GoldenCase
from ontology_engine.ingest.staging import StagingRecord
from ontology_engine.resolve.decision import Signal


class PairScorer(Protocol):
    """Anything the eval can score with: baseline, similarity, or combined."""

    matcher_kind: str

    def score(self, a: StagingRecord, b: StagingRecord) -> tuple[list[Signal], float]:
        ...


class CasePrediction(BaseModel):
    case_id: str
    kind: str
    predicted_match: bool
    confidence: float
    correct: bool


class EvalThresholds(BaseModel):
    min_precision: float = 0.95
    min_recall: float = 0.90


class EvalResult(BaseModel):
    """Precision/recall/F1 for one matcher over the golden set, with the mismatched cases."""

    matcher: str
    threshold: float
    total: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float
    recall: float
    f1: float
    mismatches: list[CasePrediction] = Field(default_factory=list)
    ran_at: datetime = Field(default_factory=datetime.utcnow)

    def gate(self, thresholds: EvalThresholds | None = None) -> tuple[bool, list[str]]:
        t = thresholds or EvalThresholds()
        reasons: list[str] = []
        if self.precision < t.min_precision:
            reasons.append(f"precision {self.precision:.3f} < {t.min_precision:.2f}")
        if self.recall < t.min_recall:
            reasons.append(f"recall {self.recall:.3f} < {t.min_recall:.2f}")
        return (not reasons), reasons


def _threshold_of(matcher: PairScorer, override: float | None) -> float:
    if override is not None:
        return override
    config = getattr(matcher, "config", None)
    return float(getattr(config, "threshold", 0.7))


def evaluate(
    matcher: PairScorer, cases: list[GoldenCase], *, threshold: float | None = None
) -> EvalResult:
    """Run `matcher` over `cases` and compute precision/recall/F1 + the mismatch list."""
    thr = _threshold_of(matcher, threshold)
    tp = fp = fn = tn = 0
    mismatches: list[CasePrediction] = []

    for case in cases:
        a = case.left.as_staging(case.object_type_key)
        b = case.right.as_staging(case.object_type_key)
        _, confidence = matcher.score(a, b)
        predicted = confidence >= thr
        correct = predicted == case.is_match

        if case.is_match and predicted:
            tp += 1
        elif case.is_match and not predicted:
            fn += 1
        elif not case.is_match and predicted:
            fp += 1
        else:
            tn += 1

        if not correct:
            mismatches.append(
                CasePrediction(
                    case_id=case.case_id,
                    kind=case.kind,
                    predicted_match=predicted,
                    confidence=round(confidence, 4),
                    correct=False,
                )
            )

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return EvalResult(
        matcher=matcher.matcher_kind,
        threshold=thr,
        total=len(cases),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_negatives=tn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        mismatches=mismatches,
    )


def write_report(result: EvalResult, path: str | Path) -> Path:
    """Write the eval result as a JSON report (consumed by CI and the eval dashboard)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return p
