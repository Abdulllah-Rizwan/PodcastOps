"""ActionDef (declarative) and ActionAttempt (audit record) — Principle IV data model.

`ActionDef` describes a registered, typed external change: its input schema, its owned target, and
which input fields form the idempotency key. `ActionAttempt` records one execution (mock or real):
every attempt is persisted, `real` requires approval, and a repeat with the same idempotency key
yields `skipped_idempotent`. The enforcing port is implemented in the US2 phase.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ActionMode = Literal["mock", "real"]
ActionStatus = Literal["mock_logged", "success", "failed", "skipped_idempotent"]
RequestedBy = Literal["operator", "agent_proposed_operator_approved"]


class ActionDef(BaseModel):
    """A registered, typed external change (the only mutation path)."""

    model_config = {"frozen": True}

    key: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    # The owned channel/target identity this action may write to (owned-target-only).
    target: str = ""
    # Which input fields compose the idempotency key.
    idempotency_key_fields: list[str] = Field(default_factory=list)


def _new_id() -> str:
    return uuid4().hex


class ActionAttempt(BaseModel):
    """One execution record for an action, mock or real."""

    id: str = Field(default_factory=_new_id)
    action_key: str
    input: dict[str, Any] = Field(default_factory=dict)
    mode: ActionMode
    idempotency_key: str
    requested_by: RequestedBy = "operator"
    approved: bool = False
    status: ActionStatus
    result: dict[str, Any] | None = None
    error: str | None = None
    attempted_at: datetime = Field(default_factory=datetime.utcnow)
