"""PostgresRepository — the Postgres + pgvector backend (production store).

SQLAlchemy 2 and pgvector are imported lazily inside the constructor so that importing the engine
(or running the hermetic JSON-backed tests) never requires the `postgres` extra. The schema is
created by the Alembic migration in ``infra/migrations`` (see T018); ``create_all()`` is offered
only as a convenience for local bring-up.

Live transport — excluded from coverage; exercised against a real Postgres in integration/deploy.
"""

from __future__ import annotations

from typing import Any

from ontology_engine.actions.attempt import ActionAttempt
from ontology_engine.embeddings.record import EmbeddingRecord
from ontology_engine.ingest.staging import StagingRecord, StagingStatus
from ontology_engine.ontology.instances import ObjectInstance
from ontology_engine.resolve.decision import ResolutionDecision
from ontology_engine.store.repository import ReadOnlyStore, ReadOnlyView

# Default embedding dimension. MiniLM (local) = 384; voyage-3 = 1024. Set to match the provider
# used to populate the column; the migration pins the same value.
DEFAULT_EMBEDDING_DIM = 384


class PostgresRepository:  # pragma: no cover - live transport
    """A Repository backed by PostgreSQL with a pgvector column for embeddings."""

    def __init__(self, database_url: str, *, embedding_dim: int = DEFAULT_EMBEDDING_DIM) -> None:
        if not database_url:
            raise ValueError("DATABASE_URL is required for PostgresRepository")
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        self._models = _build_models(embedding_dim)
        self._engine = create_engine(database_url, future=True)
        self._Session = sessionmaker(self._engine, future=True)

    def create_all(self) -> None:
        """Create tables + the vector extension (local convenience; prod uses Alembic)."""
        from sqlalchemy import text

        with self._engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        self._models.Base.metadata.create_all(self._engine)

    # --- writes ----------------------------------------------------------

    def stage(self, record: StagingRecord) -> None:
        m = self._models
        with self._Session.begin() as s:
            s.query(m.Staging).filter_by(
                source_key=record.source_key, external_id=record.external_id
            ).delete()
            s.add(
                m.Staging(
                    id=record.id,
                    data=record.model_dump(mode="json"),
                    source_key=record.source_key,
                    external_id=record.external_id,
                    status=record.status,
                )
            )

    def upsert_instance(self, instance: ObjectInstance) -> None:
        m = self._models
        with self._Session.begin() as s:
            s.merge(
                m.Instance(
                    id=instance.id,
                    object_type_key=instance.object_type_key,
                    data=instance.model_dump(mode="json"),
                    is_fused=instance.is_fused,
                )
            )

    def save_resolution(self, decision: ResolutionDecision) -> None:
        m = self._models
        with self._Session.begin() as s:
            s.query(m.Resolution).filter_by(instance_id=decision.instance_id).delete()
            s.add(
                m.Resolution(
                    id=decision.id,
                    instance_id=decision.instance_id,
                    data=decision.model_dump(mode="json"),
                )
            )

    def record_attempt(self, attempt: ActionAttempt) -> None:
        m = self._models
        with self._Session.begin() as s:
            s.add(
                m.Attempt(
                    id=attempt.id,
                    action_key=attempt.action_key,
                    idempotency_key=attempt.idempotency_key,
                    mode=attempt.mode,
                    status=attempt.status,
                    data=attempt.model_dump(mode="json"),
                )
            )

    def save_embedding(self, record: EmbeddingRecord) -> None:
        m = self._models
        with self._Session.begin() as s:
            s.merge(
                m.Embedding(
                    instance_id=record.instance_id,
                    object_type_key=record.object_type_key,
                    vector=record.vector,
                    data=record.model_dump(mode="json"),
                )
            )

    # --- reads -----------------------------------------------------------

    def get_instance(self, instance_id: str) -> ObjectInstance | None:
        m = self._models
        with self._Session() as s:
            row = s.get(m.Instance, instance_id)
            return ObjectInstance.model_validate(row.data) if row else None

    def query_instances(
        self,
        object_type_key: str,
        filters: dict[str, Any] | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ObjectInstance]:
        m = self._models
        filters = filters or {}
        with self._Session() as s:
            q = s.query(m.Instance).filter_by(object_type_key=object_type_key)
            if "fused" in filters:
                q = q.filter(m.Instance.is_fused == bool(filters["fused"]))
            q = q.order_by(m.Instance.id).offset(offset).limit(limit)
            return [ObjectInstance.model_validate(r.data) for r in q]

    def list_staging(
        self, source_key: str | None = None, status: StagingStatus | None = None
    ) -> list[StagingRecord]:
        m = self._models
        with self._Session() as s:
            q = s.query(m.Staging)
            if source_key is not None:
                q = q.filter_by(source_key=source_key)
            if status is not None:
                q = q.filter_by(status=status)
            return [StagingRecord.model_validate(r.data) for r in q]

    def get_resolution(self, instance_id: str) -> ResolutionDecision | None:
        m = self._models
        with self._Session() as s:
            row = s.query(m.Resolution).filter_by(instance_id=instance_id).one_or_none()
            return ResolutionDecision.model_validate(row.data) if row else None

    def list_attempts(
        self, action_key: str | None = None, status: str | None = None
    ) -> list[ActionAttempt]:
        m = self._models
        with self._Session() as s:
            q = s.query(m.Attempt)
            if action_key is not None:
                q = q.filter_by(action_key=action_key)
            if status is not None:
                q = q.filter_by(status=status)
            return [ActionAttempt.model_validate(r.data) for r in q]

    def find_attempt(self, idempotency_key: str) -> ActionAttempt | None:
        m = self._models
        with self._Session() as s:
            row = s.query(m.Attempt).filter_by(idempotency_key=idempotency_key, mode="real").first()
            return ActionAttempt.model_validate(row.data) if row else None

    def nearest(
        self, object_type_key: str, vector: list[float], k: int = 5
    ) -> list[tuple[ObjectInstance, float]]:
        m = self._models
        with self._Session() as s:
            q = (
                s.query(m.Embedding, m.Embedding.vector.cosine_distance(vector).label("dist"))
                .filter_by(object_type_key=object_type_key)
                .order_by("dist")
                .limit(k)
            )
            out: list[tuple[ObjectInstance, float]] = []
            for emb, dist in q:
                inst = self.get_instance(emb.instance_id)
                if inst is not None:
                    out.append((inst, 1.0 - float(dist)))  # cosine similarity
            return out

    def read_view(self) -> ReadOnlyStore:
        return ReadOnlyView(self)  # type: ignore[arg-type]


def _build_models(embedding_dim: int):  # pragma: no cover - live transport
    """Build the SQLAlchemy ORM models (imported lazily to keep the engine import light)."""
    from pgvector.sqlalchemy import Vector
    from sqlalchemy import Boolean, String
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

    class Base(DeclarativeBase):
        pass

    class Staging(Base):
        __tablename__ = "staging_records"
        id: Mapped[str] = mapped_column(String, primary_key=True)
        source_key: Mapped[str] = mapped_column(String, index=True)
        external_id: Mapped[str] = mapped_column(String, index=True)
        status: Mapped[str] = mapped_column(String, index=True)
        data: Mapped[dict] = mapped_column(JSONB)

    class Instance(Base):
        __tablename__ = "object_instances"
        id: Mapped[str] = mapped_column(String, primary_key=True)
        object_type_key: Mapped[str] = mapped_column(String, index=True)
        is_fused: Mapped[bool] = mapped_column(Boolean, index=True, default=False)
        data: Mapped[dict] = mapped_column(JSONB)

    class Resolution(Base):
        __tablename__ = "resolution_decisions"
        id: Mapped[str] = mapped_column(String, primary_key=True)
        instance_id: Mapped[str] = mapped_column(String, index=True)
        data: Mapped[dict] = mapped_column(JSONB)

    class Attempt(Base):
        __tablename__ = "action_attempts"
        id: Mapped[str] = mapped_column(String, primary_key=True)
        action_key: Mapped[str] = mapped_column(String, index=True)
        idempotency_key: Mapped[str] = mapped_column(String, index=True)
        mode: Mapped[str] = mapped_column(String, index=True)
        status: Mapped[str] = mapped_column(String, index=True)
        data: Mapped[dict] = mapped_column(JSONB)

    class Embedding(Base):
        __tablename__ = "embeddings"
        instance_id: Mapped[str] = mapped_column(String, primary_key=True)
        object_type_key: Mapped[str] = mapped_column(String, index=True)
        vector: Mapped[list[float]] = mapped_column(Vector(embedding_dim))
        data: Mapped[dict] = mapped_column(JSONB)

    class _Models:
        pass

    models = _Models()
    models.Base = Base
    models.Staging = Staging
    models.Instance = Instance
    models.Resolution = Resolution
    models.Attempt = Attempt
    models.Embedding = Embedding
    return models
