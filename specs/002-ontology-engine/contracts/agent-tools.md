# Contract — AI Agent Tools (grounded, propose-only)

The agent runs on **Claude Opus 5.5** (`claude-opus-5-5`) via the Anthropic SDK **Tool Runner**
(`client.beta.messages.tool_runner`). Its tool surface is deliberately split into **read tools**
(grounded retrieval + functions) and a single **propose tool** — the agent has **no tool that
executes an external change** (Principle VI). The ontology grounding context is wrapped in
`cache_control: {type: "ephemeral"}` for multi-turn caching.

## Read tools (map to engine FunctionDefs / Repository read-view)

- `search_objects(type, query, k)` → nearest ObjectInstances by embedding + filters; returns ids +
  key properties. (Grounded retrieval over pgvector.)
- `get_object(id)` → one ObjectInstance with properties, `source_refs`, links.
- `traverse(id, link_type)` → linked instances.
- `run_function(key, params)` → result of a registered read-only FunctionDef (e.g.
  `apple_without_youtube`).

All read tools are side-effect-free and return real object ids so the answer can cite them.

## Propose tool (never executes)

- `propose_action(action_key, input)` → records a **proposal** (ActionDef key + validated input +
  rationale). Returns the proposal id and the mock "would do X to Y" preview. It MUST NOT call the
  Action port's `execute`. Execution happens only when the operator approves via
  `POST /agent/proposals/{id}/approve`, which routes through the normal human-approved action path.

## Response contract

The agent returns a `GroundedAnswer`:
- `answer_text` — grounded in retrieved objects.
- `citations[]` — ObjectInstance ids actually used (deterministic eval checks these resolve to real
  objects).
- `proposed_actions[]` — zero or more unexecuted proposals.
- `trace_id` — Langfuse trace.

## Guardrails (enforced + evaluated)

- If the question has no grounding in the ontology, the agent states it lacks grounded data rather
  than fabricating (eval: ungrounded-question case).
- `propose_action` inputs are schema-validated against the ActionDef and checked against policy
  (owned-target-only) before the proposal is stored; invalid proposals are rejected, not surfaced as
  executable.
- Evals: deterministic (citations resolve; proposals valid) + LLM-as-judge on **Claude Haiku 5.5**
  (`claude-haiku-5-5`) for faithfulness/relevance; traces recorded for every call.
