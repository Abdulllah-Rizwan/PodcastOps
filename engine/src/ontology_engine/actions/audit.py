"""AuditTrail — the single place every ActionAttempt is logged and persisted (Principle IV).

The engine records *every* attempt, mock or real, success or failure, so the action layer is always
auditable. This wraps the `Repository` so the executor depends on one small audit seam rather than
the whole store, and emits the standardized intent line (`would publish X to Y` / `publishing X to
Y`). Carried forward from the slice's `action/audit_log.py`, now backed by the repository.
"""

from __future__ import annotations

import logging

from ontology_engine.actions.attempt import ActionAttempt, ActionMode
from ontology_engine.store.repository import Repository

_LOGGER = logging.getLogger("ontology_engine.action")


def intent_line(mode: ActionMode, change: str, target: str) -> str:
    """The human-readable audit line for an intended change (logged before any real call)."""
    verb = "would publish" if mode == "mock" else "publishing"
    return f'{verb} "{change}" to {target}'


class AuditTrail:
    """Persists and logs ActionAttempts; reads them back for the audit timeline."""

    def __init__(self, repo: Repository, logger: logging.Logger | None = None) -> None:
        self._repo = repo
        self._log = logger or _LOGGER

    def record(self, attempt: ActionAttempt) -> ActionAttempt:
        """Persist an attempt and log it. Returns the same attempt for convenience."""
        self._repo.record_attempt(attempt)
        self._log.info(
            "action attempt action=%s mode=%s status=%s key=%s approved=%s",
            attempt.action_key,
            attempt.mode,
            attempt.status,
            attempt.idempotency_key,
            attempt.approved,
        )
        return attempt

    def find(self, idempotency_key: str) -> ActionAttempt | None:
        """The prior real attempt for this idempotency key, if any (drives `skipped_idempotent`)."""
        return self._repo.find_attempt(idempotency_key)

    def recent(
        self, action_key: str | None = None, status: str | None = None
    ) -> list[ActionAttempt]:
        return self._repo.list_attempts(action_key, status)
