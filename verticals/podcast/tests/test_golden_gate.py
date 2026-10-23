"""Guards the committed podcast golden set: the baseline must clear the CI gate on it (T046–T049).

If a change to the golden data, the matcher, or the eval ever drops precision below 95% or recall
below 90%, this fails locally — the same bar CI enforces. Also checks the similarity matcher stays
runnable hermetically (HashingEmbeddings), and that the baseline remains usable on its own.
"""

from __future__ import annotations

from ontology_engine.embeddings.provider import HashingEmbeddings
from ontology_engine.evals.golden import load_golden
from ontology_engine.evals.resolution import evaluate
from ontology_engine.resolve.baseline import BaselineMatcher
from ontology_engine.resolve.similarity import CombinedMatcher, SimilarityMatcher
from vertical_podcast.registry import GOLDEN_SET_PATH


def test_golden_set_has_matches_and_hard_negatives():
    cases = load_golden(GOLDEN_SET_PATH)
    assert sum(c.is_match for c in cases) >= 150  # the ~199 real matched pairs
    assert sum(not c.is_match for c in cases) >= 20  # curated hard negatives


def test_baseline_passes_the_gate_on_the_real_golden_set():
    cases = load_golden(GOLDEN_SET_PATH)
    result = evaluate(BaselineMatcher(), cases)
    passed, reasons = result.gate()
    assert passed, reasons
    assert result.precision >= 0.95 and result.recall >= 0.90


def test_combined_matcher_runs_hermetically_and_passes():
    cases = load_golden(GOLDEN_SET_PATH)
    combined = CombinedMatcher(BaselineMatcher(), SimilarityMatcher(HashingEmbeddings()))
    result = evaluate(combined, cases)
    passed, _ = result.gate()
    assert passed
