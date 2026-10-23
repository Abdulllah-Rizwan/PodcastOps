"""Functions + actions endpoints (US2, T043) — deciding ≠ acting, writeback safe/audited.

- `GET  /functions`                list the read-only decision functions
- `POST /functions/{key}/run`      run one function (no mutation) and return its decisions
- `GET  /actions`                  list the registered actions
- `POST /actions/{key}/preview`    mock the action (logs intent, no external call)
- `POST /actions/{key}/execute`    perform the real action — requires `{"approved": true}`
- `GET  /actions/attempts`         the audit trail of every attempt

The handler that actually writes is supplied by the vertical (dependency inversion); the engine's
`ActionExecutor` enforces approval, access, and idempotency around it.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.state import AppContext, get_ctx
from ontology_engine.actions.audit import AuditTrail
from ontology_engine.actions.port import (
    ActionAccessError,
    ActionApprovalError,
    ActionExecutor,
    ActionHandler,
)
from ontology_engine.functions.registry import UnknownFunctionError, run_function

router = APIRouter(tags=["logic+action"])


class RunFunctionBody(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)


class ActionBody(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    approved: bool = False


# --- logic (functions) --------------------------------------------------


@router.get("/functions")
def list_functions(ctx: AppContext = Depends(get_ctx)) -> dict[str, object]:
    return {
        "functions": [
            {"key": f.key, "description": f.description, "input_types": f.input_types}
            for f in ctx.registry.functions()
        ]
    }


@router.post("/functions/{key}/run")
def run_fn(
    key: str, body: RunFunctionBody | None = None, ctx: AppContext = Depends(get_ctx)
) -> dict[str, object]:
    params = (body or RunFunctionBody()).params
    try:
        decisions = run_function(ctx.registry, ctx.repo, key, params)
    except UnknownFunctionError:
        raise HTTPException(status_code=404, detail=f"function {key!r} not found")
    flagged = [d for d in decisions if d.action_needed]
    return {
        "function": key,
        "total": len(decisions),
        "action_needed": len(flagged),
        "decisions": [d.model_dump() for d in decisions],
    }


# --- action -------------------------------------------------------------


def _executor(ctx: AppContext, key: str) -> ActionExecutor:
    action_def = ctx.registry.get_action(key)
    if action_def is None:
        raise HTTPException(status_code=404, detail=f"action {key!r} not found")
    handler: ActionHandler | None = ctx.action_handlers.get(key)
    if handler is None:
        raise HTTPException(status_code=501, detail=f"no handler registered for action {key!r}")
    return ActionExecutor(action_def, handler, AuditTrail(ctx.repo))


@router.get("/actions")
def list_actions(ctx: AppContext = Depends(get_ctx)) -> dict[str, object]:
    return {
        "actions": [
            {
                "key": a.key,
                "description": a.description,
                "target": a.target,
                "input_schema": a.input_schema,
                "idempotency_key_fields": a.idempotency_key_fields,
            }
            for a in ctx.registry.actions()
        ]
    }


@router.post("/actions/{key}/preview")
def preview_action(
    key: str, body: ActionBody, ctx: AppContext = Depends(get_ctx)
) -> dict[str, object]:
    attempt = _executor(ctx, key).preview(body.input)
    return attempt.model_dump(mode="json")


@router.post("/actions/{key}/execute")
def execute_action(
    key: str, body: ActionBody, ctx: AppContext = Depends(get_ctx)
) -> dict[str, object]:
    executor = _executor(ctx, key)
    try:
        attempt = executor.execute(body.input, approved=body.approved)
    except ActionApprovalError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ActionAccessError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return attempt.model_dump(mode="json")


@router.get("/actions/attempts")
def list_attempts(
    action_key: str | None = None, status: str | None = None, ctx: AppContext = Depends(get_ctx)
) -> dict[str, object]:
    attempts = ctx.repo.list_attempts(action_key, status)
    return {"attempts": [a.model_dump(mode="json") for a in attempts]}
