"""T066 — Security posture, asserted (cross-cutting; Principles IV/V/VI/VII).

Turns the security pass into executable guarantees instead of a one-off review:

1. **No secrets committed** — `.gitignore` ignores `.env`, `secrets/`, `run/`, and (when git is
   available) no secret-like file is tracked.
2. **Human-in-the-loop** — `ActionExecutor.execute` refuses unless `approved=true`.
3. **Agent cannot act** — the entire `ai/` layer contains no call to an executor's `execute`, so a
   proposal can only be carried out by a human through the API.
4. **propose_action only previews** — a recorded proposal's attempt is a mock, never a real write.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from ontology_engine.actions.attempt import ActionDef
from ontology_engine.actions.audit import AuditTrail
from ontology_engine.actions.port import ActionApprovalError, ActionExecutor, ActionOutcome
from ontology_engine.ai import propose as propose_mod
from ontology_engine.ai.propose import propose_action
from ontology_engine.store.json_repo import JsonRepository

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AI_DIR = Path(__file__).resolve().parent.parent / "src" / "ontology_engine" / "ai"

_SECRET_TRACKED_PATTERNS = (".env", "secrets/", "youtube_token", "oauth_client", "token.json")


# --- 1. no secrets committed ------------------------------------------------


def test_gitignore_covers_secrets_and_runtime_output() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    entries = {line.strip() for line in gitignore}
    for required in (".env", "secrets/", "run/"):
        assert required in entries, f".gitignore must ignore {required!r}"


def test_no_secret_like_file_is_tracked() -> None:
    if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
        pytest.skip("git not available")
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    offenders = [
        path
        for path in tracked
        if any(pat in path for pat in _SECRET_TRACKED_PATTERNS) and not path.endswith(".example")
    ]
    assert not offenders, f"secret-like files are tracked: {offenders}"


# --- 2. human-in-the-loop on execute ---------------------------------------


class _DummyHandler:
    """Minimal ActionHandler; perform() would succeed, so only the gates can stop it."""

    def describe(self, inputs: dict) -> str:
        return "noop change"

    def confirm_access(self):
        from ontology_engine.access.check import AccessCheckResult

        return AccessCheckResult(source_key="test", capability="write", ok=True, detail="ok")

    def perform(self, inputs: dict) -> ActionOutcome:
        return ActionOutcome(status="success", result={"did": "write"})


def _executor(tmp_path) -> ActionExecutor:
    action_def = ActionDef(
        key="noop",
        description="test action",
        target="test:owned",
        idempotency_key_fields=["ref"],
        input_schema={"ref": {"type": "str", "required": True}},
    )
    audit = AuditTrail(JsonRepository(tmp_path))
    return ActionExecutor(action_def, _DummyHandler(), audit)


def test_execute_refuses_without_approval(tmp_path) -> None:
    with pytest.raises(ActionApprovalError):
        _executor(tmp_path).execute({"ref": "r1"}, approved=False)


def test_execute_runs_only_when_approved(tmp_path) -> None:
    attempt = _executor(tmp_path).execute({"ref": "r1"}, approved=True)
    assert attempt.mode == "real"
    assert attempt.approved is True
    assert attempt.status == "success"


# --- 3. the agent layer has no path to execute -----------------------------


def test_ai_layer_never_calls_execute() -> None:
    offenders: list[str] = []
    for path in sorted(AI_DIR.rglob("*.py")):
        if ".execute(" in path.read_text(encoding="utf-8"):
            offenders.append(path.name)
    assert not offenders, f"ai/ modules must not call .execute(): {offenders}"


# --- 4. propose_action only ever previews (mock) ---------------------------


def test_propose_action_records_a_mock_preview_never_a_real_write(tmp_path) -> None:
    action_def = ActionDef(
        key="noop",
        description="test action",
        target="test:owned",
        idempotency_key_fields=["ref"],
        input_schema={"ref": {"type": "str", "required": True}},
    )
    audit = AuditTrail(JsonRepository(tmp_path))
    proposal = propose_action(action_def, {"ref": "r1"}, handler=_DummyHandler(), audit=audit)
    assert proposal.valid is True
    assert proposal.status == "proposed"
    assert proposal.preview is not None
    assert proposal.preview.mode == "mock"
    assert proposal.preview.approved is False
    # The proposal module must not reach the real execute path.
    assert ".execute(" not in Path(propose_mod.__file__).read_text(encoding="utf-8")
