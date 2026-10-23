"""US4 API tests (T057): the agent endpoints, hermetic (no live API key).

`/agent/ask` degrades to 503 with empty Settings (no ANTHROPIC_API_KEY). The approve path is tested
by seeding a proposal + a fake handler and asserting it routes through ActionExecutor.execute — the
same human-approved path as /actions/{key}/execute.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from ontology_engine.access.check import AccessCheckResult
from ontology_engine.actions.port import ActionOutcome
from ontology_engine.ai.propose import ActionProposal
from ontology_engine.config import Settings


class FakeHandler:
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
    return TestClient(create_app(Settings.empty(run_dir=tmp_path)))


def test_ask_without_api_key_is_503(client: TestClient) -> None:
    res = client.post("/agent/ask", json={"question": "Which episodes are Apple-only?"})
    assert res.status_code == 503
    assert "agent unavailable" in res.json()["detail"]


def test_approve_unknown_proposal_is_404(client: TestClient) -> None:
    assert client.post("/agent/proposals/nope/approve").status_code == 404


def test_approve_routes_through_execute(client: TestClient) -> None:
    ctx = client.app.state.ctx
    handler = FakeHandler()
    ctx.action_handlers["youtube_update_show_notes"] = handler
    proposal = ActionProposal(
        action_key="youtube_update_show_notes",
        input={"test_video_id": "v1", "marker_ref": "a1"},
        valid=True,
    )
    ctx.proposals[proposal.id] = proposal

    body = client.post(f"/agent/proposals/{proposal.id}/approve").json()
    assert body["attempt"]["status"] == "success"
    assert body["attempt"]["mode"] == "real"
    assert handler.performed == [{"test_video_id": "v1", "marker_ref": "a1"}]
    assert ctx.proposals[proposal.id].status == "executed"
