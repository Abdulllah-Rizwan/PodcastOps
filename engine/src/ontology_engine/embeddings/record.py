"""EmbeddingRecord — a stored vector for one object instance (pgvector in Postgres)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EmbeddingRecord(BaseModel):
    """One embedding vector produced for an instance, with provenance."""

    instance_id: str
    object_type_key: str
    provider: str  # "voyage" | "local"
    model: str
    vector: list[float]
    created_at: datetime = Field(default_factory=datetime.utcnow)
