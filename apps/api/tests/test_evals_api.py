"""US3 API tests (T050): the ER eval endpoints over the registered vertical's golden set.

Hermetic — a temp run_dir and the baseline matcher (no embeddings, no network). Verifies the run
endpoint computes + stores a gate-passing result and that `latest` returns it.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from ontology_engine.config import Settings


@pytest.fixture()
def client(tmp_path) -> TestClient:
    return TestClient(create_app(Settings.empty(run_dir=tmp_path)))


def test_latest_before_any_run_is_404(client: TestClient) -> None:
    assert client.get("/evals/resolution/latest").status_code == 404


def test_run_baseline_passes_gate_and_is_stored(client: TestClient) -> None:
    run = client.post("/evals/resolution/run?matcher=baseline").json()
    assert run["matcher"] == "baseline"
    assert run["gate"]["passed"] is True
    assert run["precision"] >= 0.95 and run["recall"] >= 0.90
    assert run["total"] >= 150

    latest = client.get("/evals/resolution/latest?matcher=baseline").json()
    assert latest["matcher"] == "baseline"
    assert latest["gate"]["passed"] is True


def test_run_combined_is_hermetic_and_passes(client: TestClient) -> None:
    run = client.post("/evals/resolution/run?matcher=combined").json()
    assert run["matcher"] == "combined"
    assert run["gate"]["passed"] is True
