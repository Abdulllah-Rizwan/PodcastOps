"""ObjectInstance and LinkInstance — rows in the ontology (Principle II).

An ObjectInstance is the clean, fused result, produced ONLY after resolution + conforming;
it is never the raw inlet (that is a StagingRecord). A fused instance carries ≥2 `source_refs`
from different sources; a single-source instance carries exactly one.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class SourceRef(BaseModel):
    """Which platform contributed to an instance, and its id there."""

    model_config = {"frozen": True}

    source_key: str  # e.g. "youtube"
    external_id: str


def _new_id() -> str:
    return uuid4().hex[:16]


class ObjectInstance(BaseModel):
    """One fused thing (≈ a row)."""

    id: str = Field(default_factory=_new_id)
    object_type_key: str
    properties: dict[str, Any] = Field(default_factory=dict)
    # ≥1 entry; a fused instance has ≥2 from different sources.
    source_refs: list[SourceRef] = Field(default_factory=list)
    embedding: list[float] | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def _check(self) -> "ObjectInstance":
        if not self.object_type_key:
            raise ValueError("ObjectInstance.object_type_key is required")
        if len(self.source_refs) < 1:
            raise ValueError("ObjectInstance must have at least one source_ref")
        return self

    @property
    def is_fused(self) -> bool:
        """True when ≥2 different sources contributed."""
        return len({ref.source_key for ref in self.source_refs}) >= 2


class LinkInstance(BaseModel):
    """A directional edge between two object instances, typed by a LinkType."""

    id: str = Field(default_factory=_new_id)
    link_type_key: str
    from_id: str  # ObjectInstance.id
    to_id: str  # ObjectInstance.id
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def _check(self) -> "LinkInstance":
        if not (self.link_type_key and self.from_id and self.to_id):
            raise ValueError("LinkInstance requires link_type_key, from_id, and to_id")
        return self
