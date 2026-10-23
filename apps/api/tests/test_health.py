"""M0 smoke test: the API boots and /health reports the registered ontology (checkpoint)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_reports_registered_ontology() -> None:
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "podcast" in body["verticals"]
    assert "episode" in body["object_types"]
    assert set(body["sources"]) == {"youtube", "apple"}
    # Storage defaults to the hermetic JSON backend unless DATABASE_URL is set.
    assert body["storage"] in {"json", "postgres"}
