"""US1 API tests (T033/T034): explorer endpoints over a seeded store, and the ingest job endpoints.

Hermetic — a temp JSON store and an empty Settings (no live targets, so ingest stages nothing and
makes no external call). Verifies the explorer surfaces fused instances with signals + confidence.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from ontology_engine.config import Settings
from ontology_engine.ontology.instances import ObjectInstance, SourceRef
from ontology_engine.resolve.decision import ResolutionDecision, Signal


@pytest.fixture()
def client(tmp_path) -> TestClient:
    app = create_app(Settings.empty(run_dir=tmp_path))
    return TestClient(app)


def _seed_fused_episode(app) -> str:
    ctx = app.state.ctx
    inst = ObjectInstance(
        object_type_key="episode",
        properties={
            "title": "The Science of Sleep",
            "published_at": "2024-03-01",
            "duration_s": 3600,
            "youtube_ref": {"external_id": "y1", "url": "https://youtu.be/y1"},
            "apple_ref": {"external_id": "a1"},
        },
        source_refs=[
            SourceRef(source_key="youtube", external_id="y1"),
            SourceRef(source_key="apple", external_id="a1"),
        ],
    )
    ctx.repo.upsert_instance(inst)
    ctx.repo.save_resolution(
        ResolutionDecision(
            object_type_key="episode",
            instance_id=inst.id,
            members=["y1", "a1"],
            signals=[Signal(name="title_similarity", value=0.95, weight=0.6, contribution=0.57)],
            confidence=0.88,
            matcher="baseline",
        )
    )
    return inst.id


def test_types_lists_episode_with_links(client: TestClient) -> None:
    body = client.get("/ontology/types").json()
    keys = {t["key"] for t in body["types"]}
    assert {"show", "episode", "guest", "clip"} <= keys
    episode = next(t for t in body["types"] if t["key"] == "episode")
    assert "title" in episode["properties"]
    assert {lk["key"] for lk in episode["links"]} >= {"belongsTo", "features", "hasClip"}


def test_instances_and_resolution(client: TestClient) -> None:
    instance_id = _seed_fused_episode(client.app)

    listing = client.get("/ontology/types/episode/instances").json()
    assert listing["count"] == 1
    item = listing["items"][0]
    assert item["is_fused"] is True
    assert item["resolution"]["matcher"] == "baseline"
    assert {r["source_key"] for r in item["source_refs"]} == {"youtube", "apple"}

    # Filter: only fused.
    fused = client.get("/ontology/types/episode/instances?fused=true").json()
    assert fused["count"] == 1

    detail = client.get(f"/ontology/instances/{instance_id}").json()
    assert detail["properties"]["title"] == "The Science of Sleep"
    assert detail["linked"] == []

    resolution = client.get(f"/ontology/instances/{instance_id}/resolution").json()
    assert resolution["confidence"] == 0.88
    assert resolution["signals"][0]["name"] == "title_similarity"


def test_unknown_type_and_instance_404(client: TestClient) -> None:
    assert client.get("/ontology/types/nope/instances").status_code == 404
    assert client.get("/ontology/instances/missing").status_code == 404


def test_ingest_run_with_no_targets_is_hermetic(client: TestClient) -> None:
    # Empty Settings → no source targets → adapters are skipped, nothing staged, no external call.
    started = client.post("/ingest/run").json()
    assert started["status"] == "completed"
    job = client.get(f"/ingest/jobs/{started['job_id']}").json()
    assert job["counts"] == {"staged": 0, "fused": 0, "single_source": 0}
