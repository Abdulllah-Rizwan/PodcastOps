"""AI agent eval harness (T052) — Principle VI: AI generation/action-selection is evaluated.

Two layers:
- **Deterministic, hermetic checks** (run in CI, no API): every citation resolves to a real
  ObjectInstance; every proposed action is schema- and policy-valid; a grounded question cites
  something, an ungrounded one cites nothing.
- **LLM-as-judge** on Claude Haiku 5.5 (`claude-haiku-5-5`) for faithfulness/relevance — a live call,
  so it is optional and guarded behind an API key (skipped when absent).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from ontology_engine.ai.agent import GroundedAnswer
from ontology_engine.ai.propose import validate_proposal

if TYPE_CHECKING:
    from ontology_engine.ontology.registry import OntologyRegistry
    from ontology_engine.store.repository import ReadOnlyStore

JUDGE_MODEL = "claude-haiku-5-5"


class DeterministicReport(BaseModel):
    """Result of the hermetic, no-API checks on one GroundedAnswer."""

    citations_ok: bool
    unresolved_citations: list[str] = Field(default_factory=list)
    proposals_ok: bool
    invalid_proposals: list[dict[str, Any]] = Field(default_factory=list)
    grounding_ok: bool

    @property
    def passed(self) -> bool:
        return self.citations_ok and self.proposals_ok and self.grounding_ok


def check_citations(answer: GroundedAnswer, view: "ReadOnlyStore") -> list[str]:
    """Return citation ids that do NOT resolve to a real ObjectInstance (should be empty)."""
    return [c.instance_id for c in answer.citations if view.get_instance(c.instance_id) is None]


def check_proposals(answer: GroundedAnswer, registry: "OntologyRegistry") -> list[dict[str, Any]]:
    """Return proposals whose inputs fail schema/policy validation (should be empty)."""
    bad: list[dict[str, Any]] = []
    for proposal in answer.proposed_actions:
        action_def = registry.get_action(proposal.action_key)
        if action_def is None:
            bad.append({"action_key": proposal.action_key, "reasons": ["unknown action"]})
            continue
        valid, reasons = validate_proposal(action_def, proposal.input)
        if not valid:
            bad.append({"action_key": proposal.action_key, "reasons": reasons})
    return bad


def evaluate_deterministic(
    answer: GroundedAnswer,
    view: "ReadOnlyStore",
    registry: "OntologyRegistry",
    *,
    expect_grounded: bool = True,
) -> DeterministicReport:
    """Run every hermetic check on one answer."""
    unresolved = check_citations(answer, view)
    invalid = check_proposals(answer, registry)
    grounding_ok = bool(answer.citations) == expect_grounded
    return DeterministicReport(
        citations_ok=not unresolved,
        unresolved_citations=unresolved,
        proposals_ok=not invalid,
        invalid_proposals=invalid,
        grounding_ok=grounding_ok,
    )


# --- LLM-as-judge (live, guarded) --------------------------------------

JUDGE_SYSTEM = (
    "You are grading an assistant's answer for FAITHFULNESS (every claim supported by the provided "
    "context) and RELEVANCE (it addresses the question). Respond with JSON only."
)


def build_judge_prompt(question: str, answer_text: str, context: str) -> str:
    return (
        f"Question:\n{question}\n\nContext (the only allowed source of truth):\n{context}\n\n"
        f"Answer to grade:\n{answer_text}\n\n"
        'Return JSON: {"faithful": bool, "relevant": bool, "rationale": "<one sentence>"}'
    )


def judge_answer(
    question: str,
    answer_text: str,
    context: str,
    *,
    api_key: str | None,
    model: str = JUDGE_MODEL,
) -> dict[str, Any]:
    """LLM-as-judge faithfulness/relevance check. Raises if no API key (caller guards/skip)."""
    if not api_key:
        raise RuntimeError("judge_answer requires an API key (live call)")
    import anthropic  # pragma: no cover - live

    client = anthropic.Anthropic(api_key=api_key)  # pragma: no cover - live
    response = client.messages.create(  # pragma: no cover - live
        model=model,
        max_tokens=512,
        system=JUDGE_SYSTEM,
        output_config={
            "format": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "faithful": {"type": "boolean"},
                        "relevant": {"type": "boolean"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["faithful", "relevant", "rationale"],
                    "additionalProperties": False,
                },
            }
        },
        messages=[{"role": "user", "content": build_judge_prompt(question, answer_text, context)}],
    )
    text = next(b.text for b in response.content if b.type == "text")  # pragma: no cover - live
    return json.loads(text)  # pragma: no cover - live
