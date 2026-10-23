"""ResolutionDecision — the inspectable record of how sources were matched (Principle III).

Every fuse of ≥2 sources carries a ResolutionDecision exposing the contributing signals and a
confidence, so a match is explainable in the explorer and gradeable in evals. Single-source
instances record "no match found" with the best rejected candidate (if any).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

MatcherKind = Literal["baseline", "similarity", "combined"]


class Signal(BaseModel):
    """One contributing signal to a match score (e.g. title_similarity=0.94)."""

    model_config = {"frozen": True}

    name: str
    value: float
    weight: float
    # weight * value — the signal's contribution to the final confidence.
    contribution: float


class RejectedCandidate(BaseModel):
    """The best candidate that was considered but not matched (for single-source instances)."""

    model_config = {"frozen": True}

    external_id: str
    source_key: str
    score: float


def _new_id() -> str:
    return uuid4().hex[:16]


class ResolutionDecision(BaseModel):
    """How a set of staging records were resolved into one ObjectInstance."""

    id: str = Field(default_factory=_new_id)
    object_type_key: str
    instance_id: str
    # The external ids / staging ids fused into the instance.
    members: list[str] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)
    confidence: float = 0.0
    matcher: MatcherKind = "baseline"
    # For single-source instances: the best candidate that was rejected, if one existed.
    rejected_best: RejectedCandidate | None = None
    decided_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def _check(self) -> "ResolutionDecision":
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be in [0, 1]")
        return self
