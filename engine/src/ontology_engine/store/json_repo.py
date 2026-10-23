"""JsonRepository — a file-backed Repository for hermetic tests, offline runs, and the CI eval.

Keeps each collection as a JSON file under a base directory. No database or network, so the
resolution eval and unit tests run with zero external dependencies (required for the CI gate).
Nearest-neighbour search is a pure-Python cosine scan — fine at the vertical #1 scale (~1k rows).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from ontology_engine.actions.attempt import ActionAttempt
from ontology_engine.embeddings.record import EmbeddingRecord
from ontology_engine.ingest.staging import StagingRecord, StagingStatus
from ontology_engine.ontology.instances import ObjectInstance
from ontology_engine.resolve.decision import ResolutionDecision
from ontology_engine.store.repository import ReadOnlyStore, ReadOnlyView


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class JsonRepository:
    """A Repository backed by JSON files. Loaded lazily and flushed on every write."""

    def __init__(self, base_dir: str | Path) -> None:
        self._dir = Path(base_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._staging: dict[str, StagingRecord] = {}
        self._instances: dict[str, ObjectInstance] = {}
        self._resolutions: dict[str, ResolutionDecision] = {}  # keyed by instance_id
        self._attempts: list[ActionAttempt] = []
        self._embeddings: dict[str, EmbeddingRecord] = {}  # keyed by instance_id
        self._load()

    # --- persistence -----------------------------------------------------

    def _path(self, name: str) -> Path:
        return self._dir / f"{name}.json"

    def _load(self) -> None:
        self._staging = {r["id"]: StagingRecord.model_validate(r) for r in self._read("staging")}
        self._instances = {
            r["id"]: ObjectInstance.model_validate(r) for r in self._read("instances")
        }
        self._resolutions = {
            r["instance_id"]: ResolutionDecision.model_validate(r)
            for r in self._read("resolutions")
        }
        self._attempts = [ActionAttempt.model_validate(r) for r in self._read("attempts")]
        self._embeddings = {
            r["instance_id"]: EmbeddingRecord.model_validate(r) for r in self._read("embeddings")
        }

    def _read(self, name: str) -> list[dict[str, Any]]:
        path = self._path(name)
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, name: str, rows: list[Any]) -> None:
        payload = [r.model_dump(mode="json") for r in rows]
        self._path(name).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # --- writes ----------------------------------------------------------

    def stage(self, record: StagingRecord) -> None:
        # Dedupe by (source_key, external_id): a re-read replaces the prior staging row.
        for existing_id, rec in list(self._staging.items()):
            if rec.source_key == record.source_key and rec.external_id == record.external_id:
                del self._staging[existing_id]
        self._staging[record.id] = record
        self._write("staging", list(self._staging.values()))

    def upsert_instance(self, instance: ObjectInstance) -> None:
        self._instances[instance.id] = instance
        self._write("instances", list(self._instances.values()))

    def save_resolution(self, decision: ResolutionDecision) -> None:
        self._resolutions[decision.instance_id] = decision
        self._write("resolutions", list(self._resolutions.values()))

    def record_attempt(self, attempt: ActionAttempt) -> None:
        self._attempts.append(attempt)
        self._write("attempts", self._attempts)

    def save_embedding(self, record: EmbeddingRecord) -> None:
        self._embeddings[record.instance_id] = record
        self._write("embeddings", list(self._embeddings.values()))

    # --- reads -----------------------------------------------------------

    def get_instance(self, instance_id: str) -> ObjectInstance | None:
        return self._instances.get(instance_id)

    def query_instances(
        self,
        object_type_key: str,
        filters: dict[str, Any] | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ObjectInstance]:
        filters = filters or {}
        out: list[ObjectInstance] = []
        for inst in self._instances.values():
            if inst.object_type_key != object_type_key:
                continue
            if "fused" in filters and inst.is_fused != bool(filters["fused"]):
                continue
            if "source" in filters and filters["source"] not in {
                ref.source_key for ref in inst.source_refs
            }:
                continue
            if not self._props_match(inst, filters):
                continue
            out.append(inst)
        out.sort(key=lambda i: i.created_at)
        return out[offset : offset + limit]

    @staticmethod
    def _props_match(inst: ObjectInstance, filters: dict[str, Any]) -> bool:
        reserved = {"fused", "source"}
        for key, value in filters.items():
            if key in reserved:
                continue
            if inst.properties.get(key) != value:
                return False
        return True

    def list_staging(
        self, source_key: str | None = None, status: StagingStatus | None = None
    ) -> list[StagingRecord]:
        out = list(self._staging.values())
        if source_key is not None:
            out = [r for r in out if r.source_key == source_key]
        if status is not None:
            out = [r for r in out if r.status == status]
        return out

    def get_resolution(self, instance_id: str) -> ResolutionDecision | None:
        return self._resolutions.get(instance_id)

    def list_attempts(
        self, action_key: str | None = None, status: str | None = None
    ) -> list[ActionAttempt]:
        out = list(self._attempts)
        if action_key is not None:
            out = [a for a in out if a.action_key == action_key]
        if status is not None:
            out = [a for a in out if a.status == status]
        return out

    def find_attempt(self, idempotency_key: str) -> ActionAttempt | None:
        for attempt in self._attempts:
            if attempt.idempotency_key == idempotency_key and attempt.mode == "real":
                return attempt
        return None

    def nearest(
        self, object_type_key: str, vector: list[float], k: int = 5
    ) -> list[tuple[ObjectInstance, float]]:
        scored: list[tuple[ObjectInstance, float]] = []
        for instance_id, rec in self._embeddings.items():
            if rec.object_type_key != object_type_key:
                continue
            inst = self._instances.get(instance_id)
            if inst is None:
                continue
            scored.append((inst, _cosine(vector, rec.vector)))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]

    def read_view(self) -> ReadOnlyStore:
        return ReadOnlyView(self)
