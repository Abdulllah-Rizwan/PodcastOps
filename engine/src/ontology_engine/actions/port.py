"""The Action port + executor — the only path that changes the world (Principle IV/V).

Deciding is not acting: a function decides, an **action** acts. The engine stays domain-agnostic —
it does not know how to call YouTube — so a vertical supplies an `ActionHandler` that does the real
write, and the engine's `ActionExecutor` enforces the safety contract around it:

- **preview** (mock): logs the intended change, makes **no** external call, records a `mock_logged`
  attempt;
- **execute** (real): refuses unless `approved=true` *and* write access is confirmed (Principle V),
  computes an idempotency key from the ActionDef's declared fields, returns `skipped_idempotent` if
  that key already succeeded, otherwise performs the write;
- **every** attempt (mock or real, success or failure) is persisted via the `AuditTrail`.

Targets are owned-only: the handler's `confirm_access` and its own target check enforce that an
action can only write to a channel we own.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ontology_engine.access.check import AccessCheckResult
from ontology_engine.actions.attempt import ActionAttempt, ActionDef, ActionStatus, RequestedBy
from ontology_engine.actions.audit import AuditTrail, intent_line

_LOGGER = logging.getLogger("ontology_engine.action")


class ActionError(RuntimeError):
    """Base class for action-layer refusals."""


class ActionApprovalError(ActionError):
    """A real execute was requested without `approved=true` (human-in-the-loop, Principle IV)."""


class ActionAccessError(ActionError):
    """Write access to the owned target could not be confirmed (Principle V)."""


@dataclass(frozen=True)
class ActionOutcome:
    """What a handler's real `perform` reports back (mapped onto the ActionAttempt)."""

    status: ActionStatus  # "success" | "skipped_idempotent" | "failed"
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@runtime_checkable
class ActionHandler(Protocol):
    """Vertical-supplied behavior for one ActionDef (dependency inversion, Principle VII)."""

    def describe(self, inputs: dict[str, Any]) -> str:
        """A human-readable summary of the intended change (used in the audit line)."""
        ...

    def confirm_access(self) -> AccessCheckResult:
        """Verify the real write is permitted against the owned target (Principle V)."""
        ...

    def perform(self, inputs: dict[str, Any]) -> ActionOutcome:
        """Do the real, idempotent, owned-target-only write. Called only after the gates pass."""
        ...


class ActionExecutor:
    """Wraps one ActionDef + its handler and enforces the safe-action contract."""

    def __init__(
        self,
        action_def: ActionDef,
        handler: ActionHandler,
        audit: AuditTrail,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._def = action_def
        self._handler = handler
        self._audit = audit
        self._log = logger or _LOGGER

    # --- idempotency ----------------------------------------------------

    def idempotency_key(self, inputs: dict[str, Any]) -> str:
        """Compose the key from the ActionDef's declared fields (readable + stable)."""
        parts = [str(inputs.get(f, "")) for f in self._def.idempotency_key_fields]
        return f"{self._def.key}:" + "|".join(parts)

    # --- preview (mock) -------------------------------------------------

    def preview(
        self, inputs: dict[str, Any], *, requested_by: RequestedBy = "operator"
    ) -> ActionAttempt:
        """Log the intended change and record a mock attempt. Makes no external call."""
        change = self._handler.describe(inputs)
        self._log.info(intent_line("mock", change, self._def.target))
        return self._audit.record(
            ActionAttempt(
                action_key=self._def.key,
                input=inputs,
                mode="mock",
                idempotency_key=self.idempotency_key(inputs),
                requested_by=requested_by,
                approved=False,
                status="mock_logged",
                result={"intended_change": change, "target": self._def.target},
            )
        )

    # --- execute (real) -------------------------------------------------

    def execute(
        self,
        inputs: dict[str, Any],
        *,
        approved: bool,
        requested_by: RequestedBy = "operator",
    ) -> ActionAttempt:
        """Perform the real write, gated by approval, access, and idempotency."""
        if not approved:
            raise ActionApprovalError(f"action {self._def.key!r} requires approved=true")

        access = self._handler.confirm_access()
        if not access.ok:
            raise ActionAccessError(
                f"write access to {self._def.target!r} not confirmed: {access.detail}"
            )

        key = self.idempotency_key(inputs)
        prior = self._audit.find(key)
        if prior is not None and prior.status in ("success", "skipped_idempotent"):
            return self._audit.record(
                ActionAttempt(
                    action_key=self._def.key,
                    input=inputs,
                    mode="real",
                    idempotency_key=key,
                    requested_by=requested_by,
                    approved=True,
                    status="skipped_idempotent",
                    result={"reason": "idempotency key already applied", "prior": prior.id},
                )
            )

        change = self._handler.describe(inputs)
        self._log.info(intent_line("real", change, self._def.target))
        try:
            outcome = self._handler.perform(inputs)
        except Exception as exc:  # noqa: BLE001 - a failed write is logged + auditable, not raised
            return self._audit.record(
                ActionAttempt(
                    action_key=self._def.key,
                    input=inputs,
                    mode="real",
                    idempotency_key=key,
                    requested_by=requested_by,
                    approved=True,
                    status="failed",
                    result={"intended_change": change},
                    error=str(exc),
                )
            )

        result = dict(outcome.result)
        result.setdefault("intended_change", change)
        return self._audit.record(
            ActionAttempt(
                action_key=self._def.key,
                input=inputs,
                mode="real",
                idempotency_key=key,
                requested_by=requested_by,
                approved=True,
                status=outcome.status,
                result=result,
                error=outcome.error,
            )
        )
