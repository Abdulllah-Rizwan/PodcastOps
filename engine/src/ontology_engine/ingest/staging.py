"""StagingRecord — raw, pre-resolution data from one source (Principle II).

Raw platform data lands here FIRST and is never presented as an object. The resolver reads
staging records and only then produces an ObjectInstance. A record's status moves
staged → resolved (fused into an instance) or staged → discarded.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

StagingStatus = Literal["staged", "resolved", "discarded"]


def _new_id() -> str:
    return uuid4().hex[:16]


class StagingRecord(BaseModel):
    """One untransformed record pulled from a single source."""

    id: str = Field(default_factory=_new_id)
    source_key: str  # e.g. "youtube"
    object_type_key: str  # which ObjectType this record will conform to, e.g. "episode"
    external_id: str  # the id on the source platform
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    status: StagingStatus = "staged"

    @model_validator(mode="after")
    def _check(self) -> "StagingRecord":
        if not (self.source_key and self.object_type_key and self.external_id):
            raise ValueError("StagingRecord requires source_key, object_type_key, and external_id")
        return self
