"""propose_action (T055) — the agent proposes; it never acts (Principle IV).

The LLM may *propose* an action, which is validated against the `ActionDef`'s input schema and the
owned-target policy and recorded as an `ActionProposal` with a **mock** preview (via the Action
port's `preview`, which logs intent and makes no external call). It MUST NOT call the port's
`execute` — a human approves the proposal through the API's `/actions/{key}/execute` path instead.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from ontology_engine.actions.attempt import ActionAttempt, ActionDef

if TYPE_CHECKING:
    from ontology_engine.actions.audit import AuditTrail
    from ontology_engine.actions.port import ActionHandler

ProposalStatus = Literal["proposed", "approved", "rejected", "executed"]


class ActionProposal(BaseModel):
    """An agent-proposed action awaiting human approval (never auto-executed)."""

    id: str = Field(default_factory=lambda: uuid4().hex[:16])
    action_key: str
    input: dict[str, Any] = Field(default_factory=dict)
    valid: bool = False
    reasons: list[str] = Field(default_factory=list)
    preview: ActionAttempt | None = None
    status: ProposalStatus = "proposed"
    created_at: datetime = Field(default_factory=datetime.utcnow)


def validate_proposal(action_def: ActionDef, inputs: dict[str, Any]) -> tuple[bool, list[str]]:
    """Check inputs against the ActionDef schema + owned-target policy (no side effects)."""
    reasons: list[str] = []

    if not action_def.target:
        reasons.append("action has no owned target configured")

    required = [
        name
        for name, spec in action_def.input_schema.items()
        if isinstance(spec, dict) and spec.get("required")
    ]
    for name in required:
        if inputs.get(name) in (None, ""):
            reasons.append(f"missing required input {name!r}")

    for name in action_def.idempotency_key_fields:
        if inputs.get(name) in (None, ""):
            reasons.append(f"missing idempotency field {name!r}")

    return (not reasons), reasons


def propose_action(
    action_def: ActionDef,
    inputs: dict[str, Any],
    *,
    handler: "ActionHandler | None" = None,
    audit: "AuditTrail | None" = None,
) -> ActionProposal:
    """Validate + record a proposal with a mock preview. Never executes the real action."""
    valid, reasons = validate_proposal(action_def, inputs)

    preview: ActionAttempt | None = None
    if valid and handler is not None and audit is not None:
        # Lazy import avoids a cycle (port imports nothing from here).
        from ontology_engine.actions.port import ActionExecutor

        executor = ActionExecutor(action_def, handler, audit)
        preview = executor.preview(inputs, requested_by="agent_proposed_operator_approved")

    return ActionProposal(
        action_key=action_def.key,
        input=inputs,
        valid=valid,
        reasons=reasons,
        preview=preview,
        status="proposed",
    )
