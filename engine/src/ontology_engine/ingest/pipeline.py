"""IngestionPipeline — orchestrates adapter → stage → resolve → object (Principle II).

The one place the stages are wired together, in order:
  1. read each registered source adapter → **stage** raw records (never objects);
  2. **block + score** the staged records with the matcher;
  3. **conform** each resolved group into an ObjectInstance (+ optional embedding);
  4. persist a **ResolutionDecision** (signals + confidence) and upsert the instance.

No path creates an ObjectInstance from a raw payload — instances come only from resolved staging.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ontology_engine.embeddings.provider import EmbeddingProvider
from ontology_engine.embeddings.record import EmbeddingRecord
from ontology_engine.ingest.staging import StagingRecord
from ontology_engine.ontology.instances import ObjectInstance
from ontology_engine.ontology.registry import OntologyRegistry
from ontology_engine.resolve.baseline import BaselineMatcher, MatchGroup
from ontology_engine.resolve.conform import conform, embedding_text
from ontology_engine.resolve.decision import ResolutionDecision
from ontology_engine.store.repository import Repository


@dataclass
class IngestResult:
    """Counts from one ingestion run (surfaced by the job status endpoint)."""

    staged: int = 0
    fused: int = 0
    single_source: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "staged": self.staged,
            "fused": self.fused,
            "single_source": self.single_source,
            "errors": self.errors,
        }


class IngestionPipeline:
    """Runs the ingest → resolve → object flow for one object type across a vertical's sources."""

    def __init__(
        self,
        registry: OntologyRegistry,
        repo: Repository,
        *,
        matcher: BaselineMatcher | None = None,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self._registry = registry
        self._repo = repo
        self._matcher = matcher or BaselineMatcher()
        self._embedder = embedder

    def run(
        self,
        source_targets: dict[str, object],
        *,
        object_type_key: str = "episode",
    ) -> IngestResult:
        object_type = self._registry.get_object_type(object_type_key)
        if object_type is None:
            raise ValueError(f"unknown object type {object_type_key!r}")

        result = IngestResult()

        # 1. Read + stage from each source that can contribute to this object type.
        staged: list[StagingRecord] = []
        for adapter in self._registry.source_adapters():
            if adapter.source_key not in object_type.source_bindings:
                continue
            target = source_targets.get(adapter.source_key)
            if not target:
                continue
            try:
                for record in adapter.read({"target": target}):
                    self._repo.stage(record)
                    staged.append(record)
                    result.staged += 1
            except Exception as exc:  # noqa: BLE001 - one source failing must not abort the run
                result.errors.append(f"{adapter.source_key} read failed: {exc}")

        # 2. Resolve the staged records into groups (block + score + assign).
        groups = self._matcher.match(staged)

        # 3. Conform each group into an ObjectInstance (+ embedding) and record the decision.
        for group in groups:
            self._materialize(object_type_key, object_type, group)
            if group.is_fused:
                result.fused += 1
            else:
                result.single_source += 1
        return result

    def _materialize(self, object_type_key: str, object_type, group: MatchGroup) -> ObjectInstance:
        properties, source_refs = conform(object_type, group.members)
        instance = ObjectInstance(
            object_type_key=object_type_key,
            properties=properties,
            source_refs=source_refs,
        )

        if self._embedder is not None:
            text = embedding_text(object_type, properties)
            if text:
                vector = self._embedder.embed([text])[0]
                instance.embedding = vector
                self._repo.save_embedding(
                    EmbeddingRecord(
                        instance_id=instance.id,
                        object_type_key=object_type_key,
                        provider=self._embedder.model_id().split(":", 1)[0],
                        model=self._embedder.model_id(),
                        vector=vector,
                    )
                )

        self._repo.upsert_instance(instance)
        self._repo.save_resolution(
            ResolutionDecision(
                object_type_key=object_type_key,
                instance_id=instance.id,
                members=[r.external_id for r in group.members],
                signals=group.signals,
                confidence=group.confidence,
                matcher=self._matcher.matcher_kind,  # "baseline"
                rejected_best=group.rejected_best,
            )
        )
        return instance
