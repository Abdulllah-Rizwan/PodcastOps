"""GoldenCase — a labeled resolution example for the ER eval (Principle III, VI).

A golden case is a pair of source records with a human label: `match` (same real-world thing) or
`non_match` (a deliberately hard near-duplicate). The eval scores each pair with a matcher and
compares the prediction to the label to compute precision/recall/F1. The data is engine-agnostic —
a vertical supplies its own `golden/cases.jsonl`; this module only defines the shape + loader.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from ontology_engine.ingest.staging import StagingRecord

GoldenKind = Literal["match", "non_match"]


class GoldenRecord(BaseModel):
    """One side of a golden pair: a source's normalized payload for the shared vocabulary."""

    source_key: str
    external_id: str
    payload: dict = Field(default_factory=dict)

    def as_staging(self, object_type_key: str) -> StagingRecord:
        """Adapt to a StagingRecord so any matcher can score it (matchers read raw_payload)."""
        return StagingRecord(
            source_key=self.source_key,
            object_type_key=object_type_key,
            external_id=self.external_id,
            raw_payload=self.payload,
        )


class GoldenCase(BaseModel):
    """A labeled pair of source records."""

    case_id: str
    kind: GoldenKind
    object_type_key: str = "episode"
    left: GoldenRecord
    right: GoldenRecord

    @property
    def is_match(self) -> bool:
        return self.kind == "match"


def load_golden(path: str | Path) -> list[GoldenCase]:
    """Load golden cases from a directory holding `cases.jsonl` (or a direct .jsonl path)."""
    p = Path(path)
    if p.is_dir():
        p = p / "cases.jsonl"
    if not p.exists():
        raise FileNotFoundError(f"golden set not found at {p}")

    cases: list[GoldenCase] = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line:
            cases.append(GoldenCase.model_validate_json(line))
    return cases
