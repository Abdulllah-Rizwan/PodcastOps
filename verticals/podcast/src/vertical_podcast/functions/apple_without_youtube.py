"""`apple_without_youtube` — the vertical #1 decision rule (read-only, Principle II).

Flags each fused `Episode` instance that is present on Apple Podcasts but not yet on YouTube — the
exact case the one writeback action addresses. Pure and read-only: it reads episodes through the
`ReadOnlyStore` it is handed and returns `Decision`s; it changes nothing (deciding ≠ acting).
Generalized from the slice's `logic/decision.py`, now reasoning over the fused ontology's
`source_refs` instead of the slice's bespoke Episode shape.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ontology_engine.functions.definitions import Decision, FunctionDef

if TYPE_CHECKING:
    from ontology_engine.store.repository import ReadOnlyStore

RULE_ID = "apple_without_youtube"
OBJECT_TYPE = "episode"


def _run(store: "ReadOnlyStore", params: dict[str, Any]) -> list[Decision]:
    limit = int(params.get("limit", 1000))
    episodes = store.query_instances(OBJECT_TYPE, limit=limit)
    decisions: list[Decision] = []
    for ep in episodes:
        sources = {ref.source_key for ref in ep.source_refs}
        needed = "apple" in sources and "youtube" not in sources
        decisions.append(
            Decision(
                instance_id=ep.id,
                action_needed=needed,
                rule=RULE_ID,
                reason=(
                    "on Apple Podcasts, not yet on YouTube"
                    if needed
                    else "no action: not an Apple-only episode"
                ),
                detail={
                    "title": ep.properties.get("title"),
                    "apple_ref": ep.properties.get("apple_ref"),
                    "sources": sorted(sources),
                },
            )
        )
    return decisions


APPLE_WITHOUT_YOUTUBE = FunctionDef(
    key=RULE_ID,
    description="Episodes on Apple Podcasts with no YouTube counterpart yet.",
    input_types=[OBJECT_TYPE],
    run=_run,
)
