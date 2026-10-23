"""The grounded, propose-only agent (T054) — Claude Opus 5.5 via the SDK Tool Runner.

The agent answers questions grounded in the ontology and may *propose* actions; it never executes
one (Principle IV/VI). Grounding tools and `propose_action` are the only ways it touches the world,
and all are read-only or proposal-only. The `anthropic` SDK is imported lazily, so importing this
module never requires it; without an API key the agent raises `AgentUnavailable` and the API layer
degrades gracefully.

Returns a `GroundedAnswer(answer_text, citations[], proposed_actions[], trace_id)`. Citations are the
real object ids the retrieval tools returned during the run, so every citation resolves to an actual
`ObjectInstance` by construction (the AI eval checks this invariant).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from ontology_engine.ai import propose as propose_mod
from ontology_engine.ai import tools as tools_mod
from ontology_engine.ai.propose import ActionProposal
from ontology_engine.ai.tracing import get_tracer

if TYPE_CHECKING:
    from ontology_engine.actions.audit import AuditTrail
    from ontology_engine.actions.port import ActionHandler
    from ontology_engine.ontology.registry import OntologyRegistry
    from ontology_engine.store.repository import ReadOnlyStore

AGENT_MODEL = "claude-opus-5-5"

SYSTEM_INSTRUCTIONS = (
    "You are the operations analyst for an ontology engine. Answer ONLY from what the grounding "
    "tools return — search_objects, get_object, traverse, run_function. Cite the real object ids "
    "you used. If the tools return nothing relevant, say you have no grounded data rather than "
    "guessing. You may PROPOSE an action with propose_action when the data warrants it, but you "
    "never execute actions — a human approves every proposal. Keep answers concise."
)


class AgentUnavailable(RuntimeError):
    """Raised when the agent cannot run (no API key, or the anthropic SDK is not installed)."""


class Citation(BaseModel):
    instance_id: str
    title: str | None = None


class GroundedAnswer(BaseModel):
    answer_text: str
    citations: list[Citation] = Field(default_factory=list)
    proposed_actions: list[ActionProposal] = Field(default_factory=list)
    trace_id: str = ""
    grounded: bool = False


class _Session:
    """Per-ask recorder: collects cited object ids and proposals the tools produce."""

    def __init__(
        self,
        view: "ReadOnlyStore",
        registry: "OntologyRegistry",
        handlers: dict[str, "ActionHandler"],
        audit: "AuditTrail | None",
    ) -> None:
        self.view = view
        self.registry = registry
        self.handlers = handlers
        self.audit = audit
        self.cited_ids: list[str] = []
        self.proposals: list[ActionProposal] = []

    def record_ids(self, ids: Any) -> None:
        for i in ids:
            if i and i not in self.cited_ids:
                self.cited_ids.append(i)


def _ontology_context(registry: "OntologyRegistry") -> str:
    """A compact, stable description of what the agent can ground in (cached as a prefix)."""
    return json.dumps(
        {
            "object_types": [
                {"key": ot.key, "description": ot.description} for ot in registry.object_types()
            ],
            "functions": [
                {"key": f.key, "description": f.description} for f in registry.functions()
            ],
            "actions": [
                {"key": a.key, "description": a.description, "input_schema": a.input_schema}
                for a in registry.actions()
            ],
        },
        ensure_ascii=False,
    )


class Agent:
    """Grounded, propose-only agent over one engine registry + read-only store."""

    def __init__(
        self,
        registry: "OntologyRegistry",
        view: "ReadOnlyStore",
        *,
        settings: Any | None = None,
        action_handlers: dict[str, "ActionHandler"] | None = None,
        audit: "AuditTrail | None" = None,
    ) -> None:
        self._registry = registry
        self._view = view
        self._settings = settings
        self._handlers = action_handlers or {}
        self._audit = audit

    def ask(self, question: str, *, max_tokens: int = 16000) -> GroundedAnswer:
        api_key = getattr(self._settings, "anthropic_api_key", None)
        if not api_key:
            raise AgentUnavailable("no ANTHROPIC_API_KEY configured")
        try:
            import anthropic
            from anthropic import beta_tool
        except ImportError as exc:  # pragma: no cover - SDK optional
            raise AgentUnavailable("the anthropic SDK is not installed") from exc

        session = _Session(self._view, self._registry, self._handlers, self._audit)
        tracer = get_tracer(self._settings)

        # --- tool closures (only model-facing params; the schema is generated from signatures) ---
        @beta_tool
        def search_objects(object_type_key: str, query: str = "") -> str:
            """Search objects of a type, optionally by a title/name substring. Returns real ids.

            Args:
                object_type_key: The object type to search, e.g. "episode".
                query: Optional case-insensitive substring to match on title/name.
            """
            results = tools_mod.search_objects(session.view, object_type_key, query or None)
            session.record_ids(r["id"] for r in results)
            return json.dumps(results, ensure_ascii=False)

        @beta_tool
        def get_object(instance_id: str) -> str:
            """Fetch one object by id, with properties, sources, and resolution.

            Args:
                instance_id: The ObjectInstance id.
            """
            result = tools_mod.get_object(session.view, instance_id)
            if result is not None:
                session.record_ids([result["id"]])
            return json.dumps(result, ensure_ascii=False)

        @beta_tool
        def traverse(instance_id: str, link_type_key: str = "") -> str:
            """Follow typed links from an object; reports the link types available from it.

            Args:
                instance_id: The ObjectInstance to traverse from.
                link_type_key: Optional link type to restrict to.
            """
            result = tools_mod.traverse(
                session.view, session.registry, instance_id, link_type_key or None
            )
            return json.dumps(result, ensure_ascii=False)

        @beta_tool
        def run_function(key: str, params: dict | None = None) -> str:
            """Run a registered read-only decision function and return its decisions.

            Args:
                key: The function key, e.g. "apple_without_youtube".
                params: Optional parameters for the function.
            """
            result = tools_mod.run_function(session.view, session.registry, key, params or {})
            for d in result.get("decisions", []):
                session.record_ids([d.get("instance_id")])
            return json.dumps(result, ensure_ascii=False)

        @beta_tool
        def propose_action(action_key: str, inputs: dict) -> str:
            """Propose an action for HUMAN approval. This does NOT execute the action.

            Args:
                action_key: The action to propose, e.g. "youtube_update_show_notes".
                inputs: The action inputs (must satisfy the action's input schema).
            """
            action_def = session.registry.get_action(action_key)
            if action_def is None:
                return json.dumps(
                    {
                        "error": f"unknown action {action_key!r}",
                        "available": [a.key for a in session.registry.actions()],
                    }
                )
            proposal = propose_mod.propose_action(
                action_def,
                inputs,
                handler=session.handlers.get(action_key),
                audit=session.audit,
            )
            session.proposals.append(proposal)
            return json.dumps(
                {
                    "proposal_id": proposal.id,
                    "valid": proposal.valid,
                    "reasons": proposal.reasons,
                    "status": "proposed — awaiting human approval (NOT executed)",
                }
            )

        system = [
            {"type": "text", "text": SYSTEM_INSTRUCTIONS},
            {
                "type": "text",
                "text": "Ontology you can ground in:\n" + _ontology_context(self._registry),
                "cache_control": {"type": "ephemeral"},
            },
        ]

        client = anthropic.Anthropic(api_key=api_key)
        with tracer.trace("agent.ask", question=question) as tr:
            runner = client.beta.messages.tool_runner(
                model=AGENT_MODEL,
                max_tokens=max_tokens,
                thinking={"type": "adaptive"},
                system=system,
                tools=[search_objects, get_object, traverse, run_function, propose_action],
                messages=[{"role": "user", "content": question}],
            )
            last = None
            for message in runner:  # the SDK drives the tool loop to completion
                last = message
            answer_text = "".join(b.text for b in last.content if b.type == "text") if last else ""
            trace_id = tr.id

        citations = []
        for iid in session.cited_ids:
            inst = self._view.get_instance(iid)
            if inst is not None:
                citations.append(Citation(instance_id=iid, title=inst.properties.get("title")))

        return GroundedAnswer(
            answer_text=answer_text,
            citations=citations,
            proposed_actions=session.proposals,
            trace_id=trace_id,
            grounded=bool(citations),
        )
