"""M0 smoke tests: the engine foundation imports, the JSON store round-trips, and the
read-only view genuinely has no write methods (Principle II enforced by type)."""

from __future__ import annotations

from ontology_engine.actions.attempt import ActionAttempt
from ontology_engine.ingest.staging import StagingRecord
from ontology_engine.ontology.instances import ObjectInstance, SourceRef
from ontology_engine.ontology.registry import OntologyRegistry, Vertical
from ontology_engine.ontology.types import ObjectType, PropertySpec
from ontology_engine.resolve.decision import ResolutionDecision, Signal
from ontology_engine.store.json_repo import JsonRepository


def test_object_instance_fusion_flag() -> None:
    single = ObjectInstance(
        object_type_key="episode", source_refs=[SourceRef(source_key="apple", external_id="a1")]
    )
    fused = ObjectInstance(
        object_type_key="episode",
        source_refs=[
            SourceRef(source_key="apple", external_id="a1"),
            SourceRef(source_key="youtube", external_id="y1"),
        ],
    )
    assert single.is_fused is False
    assert fused.is_fused is True


def test_object_instance_requires_source_ref() -> None:
    import pytest

    with pytest.raises(ValueError):
        ObjectInstance(object_type_key="episode", source_refs=[])


def test_json_repository_round_trip(tmp_path) -> None:
    repo = JsonRepository(tmp_path)
    repo.stage(StagingRecord(source_key="youtube", object_type_key="episode", external_id="y1"))
    inst = ObjectInstance(
        object_type_key="episode",
        properties={"title": "Hello"},
        source_refs=[
            SourceRef(source_key="youtube", external_id="y1"),
            SourceRef(source_key="apple", external_id="a1"),
        ],
    )
    repo.upsert_instance(inst)
    repo.save_resolution(
        ResolutionDecision(
            object_type_key="episode",
            instance_id=inst.id,
            members=["y1", "a1"],
            signals=[Signal(name="title_similarity", value=0.94, weight=0.6, contribution=0.56)],
            confidence=0.9,
            matcher="baseline",
        )
    )

    # A fresh repo over the same dir sees the persisted rows.
    reloaded = JsonRepository(tmp_path)
    assert reloaded.get_instance(inst.id) is not None
    assert len(reloaded.list_staging(source_key="youtube")) == 1
    assert reloaded.get_resolution(inst.id).confidence == 0.9
    fused = reloaded.query_instances("episode", {"fused": True})
    assert len(fused) == 1


def test_find_attempt_idempotency(tmp_path) -> None:
    repo = JsonRepository(tmp_path)
    repo.record_attempt(
        ActionAttempt(
            action_key="noop", idempotency_key="k1", mode="real", status="success", approved=True
        )
    )
    assert repo.find_attempt("k1") is not None
    assert repo.find_attempt("other") is None


def test_read_view_has_no_write_methods(tmp_path) -> None:
    view = JsonRepository(tmp_path).read_view()
    for writer in (
        "stage",
        "upsert_instance",
        "save_resolution",
        "record_attempt",
        "save_embedding",
    ):
        assert not hasattr(view, writer), f"read view must not expose {writer}"
    assert hasattr(view, "get_instance")


def test_registry_rejects_duplicate_vertical() -> None:
    import pytest

    reg = OntologyRegistry()
    ot = ObjectType(key="thing", properties={"name": PropertySpec(type="str")})
    reg.register(Vertical(key="v1", object_types=[ot]))
    with pytest.raises(Exception):
        reg.register(Vertical(key="v1"))
