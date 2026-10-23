"""T038 — the action seam (Principle IV/V), tested without any vertical.

Covers the whole safe-action contract with a fake handler:
- **mock** preview makes no external call and logs the intended change;
- **real** execute refuses unless `approved=true`;
- a repeat with the same idempotency key yields `skipped_idempotent` (no second real call);
- write access must be confirmed before a real call;
- **every** attempt (mock, real, skipped) is persisted.
"""

from __future__ import annotations

import logging

import pytest

from ontology_engine.access.check import AccessCheckResult
from ontology_engine.actions.attempt import ActionDef
from ontology_engine.actions.audit import AuditTrail
from ontology_engine.actions.port import (
    ActionAccessError,
    ActionApprovalError,
    ActionExecutor,
    ActionOutcome,
)
from ontology_engine.store.json_repo import JsonRepository

ACTION = ActionDef(
    key="demo_write",
    description="demo",
    target="fake:owned",
    idempotency_key_fields=["ref"],
)
INPUTS = {"ref": "ep-1"}


class FakeHandler:
    """A minimal ActionHandler recording its real calls."""

    def __init__(self, *, access_ok: bool = True) -> None:
        self.access_ok = access_ok
        self.performed: list[dict] = []

    def describe(self, inputs: dict) -> str:
        return f"link {inputs.get('ref')}"

    def confirm_access(self) -> AccessCheckResult:
        return AccessCheckResult(
            source_key="fake", capability="write", ok=self.access_ok, detail="test"
        )

    def perform(self, inputs: dict) -> ActionOutcome:
        self.performed.append(inputs)
        return ActionOutcome(status="success", result={"did": inputs["ref"]})


def _executor(tmp_path, handler: FakeHandler) -> tuple[ActionExecutor, JsonRepository]:
    repo = JsonRepository(tmp_path / "store")
    return ActionExecutor(ACTION, handler, AuditTrail(repo)), repo


def test_preview_is_mock_only_and_logs_intent(tmp_path, caplog):
    handler = FakeHandler()
    executor, repo = _executor(tmp_path, handler)

    with caplog.at_level(logging.INFO, logger="ontology_engine.action"):
        attempt = executor.preview(INPUTS)

    assert attempt.mode == "mock"
    assert attempt.status == "mock_logged"
    assert handler.performed == []  # no external call
    assert any(
        "would publish" in r.message or "would publish" in r.getMessage() for r in caplog.records
    )
    assert len(repo.list_attempts()) == 1  # the mock attempt is recorded


def test_real_execute_requires_approval(tmp_path):
    handler = FakeHandler()
    executor, repo = _executor(tmp_path, handler)

    with pytest.raises(ActionApprovalError):
        executor.execute(INPUTS, approved=False)

    assert handler.performed == []
    assert repo.list_attempts() == []  # nothing was attempted


def test_real_execute_requires_confirmed_access(tmp_path):
    handler = FakeHandler(access_ok=False)
    executor, _ = _executor(tmp_path, handler)

    with pytest.raises(ActionAccessError):
        executor.execute(INPUTS, approved=True)

    assert handler.performed == []


def test_approved_execute_performs_then_is_idempotent(tmp_path):
    handler = FakeHandler()
    executor, repo = _executor(tmp_path, handler)

    first = executor.execute(INPUTS, approved=True)
    assert first.mode == "real"
    assert first.status == "success"
    assert handler.performed == [INPUTS]

    second = executor.execute(INPUTS, approved=True)
    assert second.status == "skipped_idempotent"
    assert handler.performed == [INPUTS]  # NOT called a second time


def test_every_attempt_is_recorded(tmp_path):
    handler = FakeHandler()
    executor, repo = _executor(tmp_path, handler)

    executor.preview(INPUTS)
    executor.execute(INPUTS, approved=True)
    executor.execute(INPUTS, approved=True)

    attempts = repo.list_attempts(action_key="demo_write")
    assert [a.status for a in attempts] == ["mock_logged", "success", "skipped_idempotent"]
