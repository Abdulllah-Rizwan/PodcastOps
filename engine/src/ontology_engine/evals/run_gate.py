"""CI entry point for the entity-resolution eval gate (T049, SC-002/SC-007).

Runs the hermetic ER eval against a golden set and exits non-zero if the gate fails (precision < 95%
or recall < 90%). Deterministic and dependency-light: the default `baseline` matcher needs no
embeddings; `combined` uses `HashingEmbeddings`, which is pure Python — so CI needs no model download
or network.

Usage:
    python -m ontology_engine.evals.run_gate <golden_dir> [baseline|combined] [report_path]
"""

from __future__ import annotations

import sys

from ontology_engine.embeddings.provider import HashingEmbeddings
from ontology_engine.evals.golden import load_golden
from ontology_engine.evals.resolution import EvalThresholds, evaluate, write_report
from ontology_engine.resolve.baseline import BaselineMatcher
from ontology_engine.resolve.similarity import CombinedMatcher, SimilarityMatcher


def build_matcher(kind: str):
    if kind == "baseline":
        return BaselineMatcher()
    if kind == "combined":
        return CombinedMatcher(BaselineMatcher(), SimilarityMatcher(HashingEmbeddings()))
    raise SystemExit(f"unknown matcher {kind!r} (expected 'baseline' or 'combined')")


def main(argv: list[str]) -> int:
    golden_dir = argv[1] if len(argv) > 1 else "verticals/podcast/evals/golden"
    kind = argv[2] if len(argv) > 2 else "baseline"
    report_path = argv[3] if len(argv) > 3 else "run/evals/resolution.json"

    cases = load_golden(golden_dir)
    result = evaluate(build_matcher(kind), cases)
    write_report(result, report_path)

    passed, reasons = result.gate(EvalThresholds())
    print(
        f"[er-eval] matcher={result.matcher} cases={result.total} "
        f"P={result.precision:.3f} R={result.recall:.3f} F1={result.f1:.3f} "
        f"(tp={result.true_positives} fp={result.false_positives} "
        f"fn={result.false_negatives} tn={result.true_negatives})"
    )
    if not passed:
        print("[er-eval] GATE FAILED: " + "; ".join(reasons))
        for m in result.mismatches[:20]:
            print(
                f"  mismatch {m.case_id} kind={m.kind} predicted={m.predicted_match} "
                f"conf={m.confidence}"
            )
        return 1
    print("[er-eval] GATE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
