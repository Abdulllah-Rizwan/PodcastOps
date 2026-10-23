"""The Repository port + a read-only view (Principle II/VII).

`Repository` is the full store (stage, objects, resolutions, audit, embeddings). `ReadOnlyStore`
is the strictly-read subset. Read-only functions (Principle II) only ever receive `read_view()`,
which returns an object exposing no write methods — so a function *cannot* mutate the store, by
type. Backends: `JsonRepository` (hermetic tests/offline) and `PostgresRepository` (pgvector).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ontology_engine.actions.attempt import ActionAttempt
from ontology_engine.embeddings.record import EmbeddingRecord
from ontology_engine.ingest.staging import StagingRecord, StagingStatus
from ontology_engine.ontology.instances import ObjectInstance
from ontology_engine.resolve.decision import ResolutionDecision


@runtime_checkable
class ReadOnlyStore(Protocol):
    """The read-only handle functions receive — no write methods exist on it."""

    def get_instance(self, instance_id: str) -> ObjectInstance | None:
        ...

    def query_instances(
        self,
        object_type_key: str,
        filters: dict[str, Any] | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ObjectInstance]:
        ...

    def list_staging(
        self, source_key: str | None = None, status: StagingStatus | None = None
    ) -> list[StagingRecord]:
        ...

    def get_resolution(self, instance_id: str) -> ResolutionDecision | None:
        ...

    def list_attempts(
        self, action_key: str | None = None, status: str | None = None
    ) -> list[ActionAttempt]:
        ...

    def nearest(
        self, object_type_key: str, vector: list[float], k: int = 5
    ) -> list[tuple[ObjectInstance, float]]:
        ...


@runtime_checkable
class Repository(ReadOnlyStore, Protocol):
    """The full store: all reads plus the writes. `read_view()` narrows it to ReadOnlyStore."""

    def stage(self, record: StagingRecord) -> None:
        ...

    def upsert_instance(self, instance: ObjectInstance) -> None:
        ...

    def save_resolution(self, decision: ResolutionDecision) -> None:
        ...

    def record_attempt(self, attempt: ActionAttempt) -> None:
        ...

    def find_attempt(self, idempotency_key: str) -> ActionAttempt | None:
        ...

    def save_embedding(self, record: EmbeddingRecord) -> None:
        ...

    def read_view(self) -> ReadOnlyStore:
        ...


class ReadOnlyView:
    """Wraps a Repository and exposes only its read methods (handed to functions)."""

    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def get_instance(self, instance_id: str) -> ObjectInstance | None:
        return self._repo.get_instance(instance_id)

    def query_instances(
        self,
        object_type_key: str,
        filters: dict[str, Any] | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ObjectInstance]:
        return self._repo.query_instances(object_type_key, filters, limit=limit, offset=offset)

    def list_staging(
        self, source_key: str | None = None, status: StagingStatus | None = None
    ) -> list[StagingRecord]:
        return self._repo.list_staging(source_key, status)

    def get_resolution(self, instance_id: str) -> ResolutionDecision | None:
        return self._repo.get_resolution(instance_id)

    def list_attempts(
        self, action_key: str | None = None, status: str | None = None
    ) -> list[ActionAttempt]:
        return self._repo.list_attempts(action_key, status)

    def nearest(
        self, object_type_key: str, vector: list[float], k: int = 5
    ) -> list[tuple[ObjectInstance, float]]:
        return self._repo.nearest(object_type_key, vector, k)
