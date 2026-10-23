"""Similarity + combined matchers (Principle III).

The `BaselineMatcher` (deterministic, lexical) stays the floor and MUST remain runnable alone so any
upgrade can be measured against it. This module adds:

- `SimilarityMatcher`: scores a pair by embedding cosine (semantic closeness), via an injected
  `EmbeddingProvider`. Online it uses the pgvector `nearest` index; here it scores a given pair.
- `CombinedMatcher`: blends baseline + similarity into one confidence and merges both sets of
  `Signal`s, so the decision stays inspectable (you can see which signals drove it).

All three expose the same `score(a, b) -> (signals, confidence)` surface and a `matcher_kind`, so the
eval harness and the ingest pipeline can use any of them interchangeably.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ontology_engine.embeddings.provider import EmbeddingProvider
from ontology_engine.ingest.staging import StagingRecord
from ontology_engine.resolve.baseline import BaselineMatcher, normalize_title
from ontology_engine.resolve.decision import Signal


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


@dataclass(frozen=True)
class SimilarityConfig:
    text_fields: tuple[str, ...] = ("title", "description")
    weight: float = 1.0
    threshold: float = 0.75


class SimilarityMatcher:
    """Embedding-cosine matcher. Caches embeddings by text (the eval scores many pairs)."""

    matcher_kind = "similarity"

    def __init__(self, embedder: EmbeddingProvider, config: SimilarityConfig | None = None) -> None:
        self._embedder = embedder
        self.config = config or SimilarityConfig()
        self._cache: dict[str, list[float]] = {}

    def _text(self, record: StagingRecord) -> str:
        parts = [str(record.raw_payload.get(f, "") or "") for f in self.config.text_fields]
        return normalize_title(" ".join(p for p in parts if p))

    def _vector(self, text: str) -> list[float]:
        if text not in self._cache:
            self._cache[text] = self._embedder.embed([text])[0]
        return self._cache[text]

    def score(self, a: StagingRecord, b: StagingRecord) -> tuple[list[Signal], float]:
        cos = _cosine(self._vector(self._text(a)), self._vector(self._text(b)))
        value = max(0.0, min(1.0, cos))  # clamp to [0, 1] for a confidence reading
        signal = Signal(
            name="embedding_cosine",
            value=round(value, 4),
            weight=self.config.weight,
            contribution=round(self.config.weight * value, 4),
        )
        return [signal], round(value, 4)


@dataclass(frozen=True)
class CombinedConfig:
    baseline_weight: float = 0.6
    similarity_weight: float = 0.4
    threshold: float = 0.72


class CombinedMatcher:
    """Weighted blend of baseline + similarity; keeps both signal sets for inspectability."""

    matcher_kind = "combined"

    def __init__(
        self,
        baseline: BaselineMatcher,
        similarity: SimilarityMatcher,
        config: CombinedConfig | None = None,
    ) -> None:
        self._baseline = baseline
        self._similarity = similarity
        self.config = config or CombinedConfig()

    def score(self, a: StagingRecord, b: StagingRecord) -> tuple[list[Signal], float]:
        b_signals, b_conf = self._baseline.score(a, b)
        s_signals, s_conf = self._similarity.score(a, b)
        confidence = self.config.baseline_weight * b_conf + self.config.similarity_weight * s_conf
        return b_signals + s_signals, round(confidence, 4)
