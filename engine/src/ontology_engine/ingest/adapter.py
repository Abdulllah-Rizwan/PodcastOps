"""SourceAdapter — the ingestion inlet port (Principle VII dependency inversion).

Generalized from the slice's YouTube/Apple gateways. An adapter reads raw data from one
source into StagingRecords (never ObjectInstances — Principle II), declares what it can do
(read/write), and confirms access before modeling (Principle V). A vertical supplies concrete
adapters; tests use fakes.
"""

from __future__ import annotations

from typing import Iterable, Literal, Mapping, Protocol, runtime_checkable

from pydantic import BaseModel

from ontology_engine.access.check import AccessCheckResult
from ontology_engine.ingest.staging import StagingRecord

Capability = Literal["read", "write"]


class Capabilities(BaseModel):
    """What a source adapter is able to do; feeds the access check."""

    model_config = {"frozen": True}

    read: bool = False
    write: bool = False

    def supports(self, capability: Capability) -> bool:
        return getattr(self, capability, False)


@runtime_checkable
class SourceAdapter(Protocol):
    """Port for a single external source (one platform)."""

    source_key: str

    def read(self, config: Mapping[str, object]) -> Iterable[StagingRecord]:
        """Yield raw payloads tagged with source_key/external_id/object_type_key.

        MUST NOT create ObjectInstances. Idempotent re-reads are allowed; staging dedupes by
        (source_key, external_id).
        """
        ...

    def capabilities(self) -> Capabilities:
        """Declare read/write support for the access check."""
        ...

    def confirm_access(self, capability: Capability) -> AccessCheckResult:
        """Principle V gate: verify the planned read/write is actually permitted."""
        ...
