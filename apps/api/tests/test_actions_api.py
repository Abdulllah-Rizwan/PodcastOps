"""US2 API tests (T043): the functions + actions endpoints, end to end over a seeded store.

Hermetic — a temp JSON store, empty Settings, and (for the real-execute path) a fake action handler
swapped into the app context so no live YouTube call is made. Verifies deciding ≠ acting and the
safe/approved/idempotent/audited action contract through HTTP.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from ontology_engine.access.check import AccessCheckResult
from ontology_engine.actions.port import ActionOutcome
from ontology_engine.config import Settings
from ontology_engine.ontology.instances import ObjectInstance, SourceRef


class FakeHandler:
    """Stand-in writeback handler (no network) for the execute path."""

    def __init__(self) -> None:
        self.performed: list[dict] = []

    def describe(self, inputs: dict) -> str:
        return f"link {inputs.get('marker_ref')}"

    def confirm_access(self) -> AccessCheckResult:
        return AccessCheckResult(source_key="youtube", capability="write", ok=True, detail="test")

    def perform(self, inputs: dict) -> ActionOutcome:
        self.performed.append(inputs)
        return ActionOutcome(status="success", result={"marker": inputs.get("marker_ref")})


@pytest.fixture()
def client(tmp_path) -> TestClient:
    app = create_app(Settings.empty(run_dir=tmp_path))
    return TestClient(app)


def _seed_apple_only(app) -> str:
    inst = ObjectInstance(
        object_type_key="episode",
        properties={"title": "Apple-only ep", "apple_ref": {"external_id": "a1"}},
        source_refs=[SourceRef(source_key="apple", external_id="a1")],
    )
    app.state.ctx.repo.upsert_instance(inst)
    return inst.id


def test_functions_listed_and_run_flags_apple_only(client: TestClient) -> None:
    instance_id = _seed_apple_only(client.app)

    listed = client.get("/functions").json()
    assert "apple_without_youtube" in {f["key"] for f in listed["functions"]}

    run = client.post("/functions/apple_without_youtube/run").json()
    assert run["action_needed"] == 1
    flagged = [d for d in run["decisions"] if d["action_needed"]]
    assert flagged[0]["instance_id"] == instance_id


def test_actions_listed(client: TestClient) -> None:
    body = client.get("/actions").json()
    action = next(a for a in body["actions"] if a["key"] == "youtube_update_show_notes")
    assert action["idempotency_key_fields"] == ["test_video_id", "marker_ref"]


def test_preview_is_mock_and_execute_requires_approval(client: TestClient) -> None:
    payload = {"input": {"test_video_id": "v1", "marker_ref": "a1"}}

    preview = client.post("/actions/youtube_update_show_notes/preview", json=payload).json()
    assert preview["mode"] == "mock"
    assert preview["status"] == "mock_logged"

    # Unapproved real execute is refused.
    refused = client.post("/actions/youtube_update_show_notes/execute", json=payload)
    assert refused.status_code == 403


def test_approved_execute_is_performed_then_idempotent(client: TestClient) -> None:
    handler = FakeHandler()
    client.app.state.ctx.action_handlers["youtube_update_show_notes"] = handler
    payload = {"input": {"test_video_id": "v1", "marker_ref": "a1"}, "approved": True}

    first = client.post("/actions/youtube_update_show_notes/execute", json=payload).json()
    assert first["status"] == "success"
    second = client.post("/actions/youtube_update_show_notes/execute", json=payload).json()
    assert second["status"] == "skipped_idempotent"
    assert handler.performed == [{"test_video_id": "v1", "marker_ref": "a1"}]  # performed once

    attempts = client.get("/actions/attempts").json()["attempts"]
    assert [a["status"] for a in attempts] == ["success", "skipped_idempotent"]
