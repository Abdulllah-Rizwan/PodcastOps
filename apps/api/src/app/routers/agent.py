"""Grounded agent endpoints (US4, T057) — propose-only; a human approves to act.

- `POST /agent/ask`                     answer grounded in the ontology (citations + proposals)
- `POST /agent/proposals/{id}/approve`  route an agent proposal through the human-approved execute path

`/agent/ask` degrades gracefully when no `ANTHROPIC_API_KEY` is configured (503), so the stack stays
runnable and testable offline. Approval goes through the **same** `ActionExecutor.execute` path as
`/actions/{key}/execute` — the agent never executes anything itself (Principle IV).
"""

from __future__ import annotations

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
from ontology_engine.ai.agent import Agent, AgentUnavailable

router = APIRouter(tags=["agent"])


class AskBody(BaseModel):
    question: str = Field(min_length=1)


@router.post("/agent/ask")
def ask(body: AskBody, ctx: AppContext = Depends(get_ctx)) -> dict[str, object]:
    agent = Agent(
        ctx.registry,
        ctx.repo.read_view(),
        settings=ctx.settings,
        action_handlers=ctx.action_handlers,
        audit=AuditTrail(ctx.repo),
    )
    try:
        answer = agent.ask(body.question)
    except AgentUnavailable as exc:
        raise HTTPException(status_code=503, detail=f"agent unavailable: {exc}")

    # Persist proposals so they can be approved + executed later.
    for proposal in answer.proposed_actions:
        ctx.proposals[proposal.id] = proposal

    return answer.model_dump(mode="json")


@router.post("/agent/proposals/{proposal_id}/approve")
def approve(proposal_id: str, ctx: AppContext = Depends(get_ctx)) -> dict[str, object]:
    proposal = ctx.proposals.get(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"proposal {proposal_id!r} not found")

    action_def = ctx.registry.get_action(proposal.action_key)
    if action_def is None:
        raise HTTPException(status_code=404, detail=f"action {proposal.action_key!r} not found")
    handler: ActionHandler | None = ctx.action_handlers.get(proposal.action_key)
    if handler is None:
        raise HTTPException(
            status_code=501, detail=f"no handler registered for action {proposal.action_key!r}"
        )

    executor = ActionExecutor(action_def, handler, AuditTrail(ctx.repo))
    try:
        # Human-in-the-loop: hitting this endpoint IS the approval (Principle IV).
        attempt = executor.execute(
            proposal.input, approved=True, requested_by="agent_proposed_operator_approved"
        )
    except ActionApprovalError as exc:  # defensive; approved=True here
        raise HTTPException(status_code=403, detail=str(exc))
    except ActionAccessError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    proposal.status = "executed"
    return {"proposal_id": proposal_id, "attempt": attempt.model_dump(mode="json")}
