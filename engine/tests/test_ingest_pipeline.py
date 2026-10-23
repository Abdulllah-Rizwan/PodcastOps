"""T028 (US1) — the ingest pipeline honors stage separation (Principle II).

An ObjectInstance is created ONLY from resolved staging records, never directly from a raw payload;
a record with no cross-source match stays single-source. Uses local fake adapters + a local object
type so the engine test imports no vertical (Principle I seam).
"""

from __future__ import annotations

from typing import Iterable, Mapping

from ontology_engine.access.check import AccessCheckResult
from ontology_engine.ingest.adapter import Capabilities, Capability
from ontology_engine.ingest.pipeline import IngestionPipeline
from ontology_engine.ingest.staging import StagingRecord
from ontology_engine.ontology.registry import OntologyRegistry, Vertical
from ontology_engine.ontology.types import ObjectType, PropertySpec
from ontology_engine.store.json_repo import JsonRepository

EPISODE = ObjectType(
    key="episode",
    properties={
        "title": PropertySpec(type="str", required=True, identifying=True),
        "published_at": PropertySpec(type="date", identifying=True),
        "duration_s": PropertySpec(type="int"),
        "s1_ref": PropertySpec(type="json"),
        "s2_ref": PropertySpec(type="json"),
    },
    embeddable_fields=["title"],
    source_bindings=["s1", "s2"],
)


class FakeAdapter:
    def __init__(self, source_key: str, records: list[StagingRecord]) -> None:
        self.source_key = source_key
        self._records = records

    def capabilities(self) -> Capabilities:
        return Capabilities(read=True, write=False)

    def confirm_access(self, capability: Capability) -> AccessCheckResult:
        return AccessCheckResult(source_key=self.source_key, capability=capability, ok=True)

    def read(self, config: Mapping[str, object]) -> Iterable[StagingRecord]:
        return list(self._records)


def _rec(source: str, ext: str, title: str, date: str, dur: int) -> StagingRecord:
    return StagingRecord(
        source_key=source,
        object_type_key="episode",
        external_id=ext,
        raw_payload={"title": title, "published_at": date, "duration_s": dur, "_raw": {"x": 1}},
    )


def _pipeline(tmp_path, s1_records, s2_records):
    registry = OntologyRegistry()
    registry.register(
        Vertical(
            key="t",
            object_types=[EPISODE],
            source_adapters=[FakeAdapter("s1", s1_records), FakeAdapter("s2", s2_records)],
        )
    )
    repo = JsonRepository(tmp_path)
    return IngestionPipeline(registry, repo), repo


def test_instance_only_from_resolved_staging(tmp_path) -> None:
    s1 = [_rec("s1", "x1", "The Science of Sleep", "2024-03-01", 3600)]
    s2 = [_rec("s2", "z1", "The Science of Sleep (Full)", "2024-03-01", 3590)]
    pipeline, repo = _pipeline(tmp_path, s1, s2)

    # Nothing exists before the run.
    assert repo.query_instances("episode") == []

    result = pipeline.run({"s1": "src1", "s2": "src2"}, object_type_key="episode")

    staged = repo.list_staging()
    instances = repo.query_instances("episode")
    staged_ids = {r.external_id for r in staged}

    # Both raw records were staged first.
    assert staged_ids == {"x1", "z1"}
    assert result.staged == 2
    # Exactly one fused instance, and EVERY instance's source_refs trace back to staged records.
    assert result.fused == 1 and result.single_source == 0
    assert len(instances) == 1
    for inst in instances:
        for ref in inst.source_refs:
            assert ref.external_id in staged_ids
    # The resolution decision is persisted with signals + confidence (Principle III).
    decision = repo.get_resolution(instances[0].id)
    assert decision is not None and decision.matcher == "baseline"
    assert decision.confidence >= 0.70 and len(decision.signals) == 3
    # Conform populated the per-source refs declared on the type.
    props = instances[0].properties
    assert props["title"]
    assert props["s1_ref"]["external_id"] == "x1"
    assert props["s2_ref"]["external_id"] == "z1"


def test_single_source_stays_single_source(tmp_path) -> None:
    s1 = [_rec("s1", "x1", "Solo Episode on Focus", "2024-03-01", 3600)]
    s2 = [_rec("s2", "z1", "A Totally Different Topic", "2024-03-10", 900)]
    pipeline, repo = _pipeline(tmp_path, s1, s2)

    result = pipeline.run({"s1": "src1", "s2": "src2"}, object_type_key="episode")

    assert result.fused == 0
    assert result.single_source == 2
    instances = repo.query_instances("episode")
    assert len(instances) == 2
    assert all(not inst.is_fused for inst in instances)
    assert all(len(inst.source_refs) == 1 for inst in instances)
