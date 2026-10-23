"""Grounded retrieval tools (T053) — side-effect-free reads over the ontology (Principle VI).

The agent sees the world *only* through these: they take a `ReadOnlyStore` (no write method
reachable) and return real `ObjectInstance` ids, so every answer can be grounded in — and cited back
to — actual objects. `run_function` runs a registered read-only function (deciding ≠ acting). None of
these mutate anything; `propose_action` (the one write-adjacent capability) lives in `propose.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ontology_engine.ontology.registry import OntologyRegistry

if TYPE_CHECKING:
    from ontology_engine.ontology.instances import ObjectInstance
    from ontology_engine.store.repository import ReadOnlyStore


def _summarize(inst: "ObjectInstance") -> dict[str, Any]:
    return {
        "id": inst.id,
        "object_type": inst.object_type_key,
        "title": inst.properties.get("title") or inst.properties.get("name"),
        "sources": sorted({ref.source_key for ref in inst.source_refs}),
        "is_fused": inst.is_fused,
    }


def search_objects(
    view: "ReadOnlyStore",
    object_type_key: str,
    query: str | None = None,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Find objects of a type, optionally filtered by a case-insensitive title/name substring."""
    instances = view.query_instances(object_type_key, limit=max(limit * 5, limit))
    if query:
        q = query.lower()
        instances = [
            i
            for i in instances
            if q in str(i.properties.get("title") or i.properties.get("name") or "").lower()
        ]
    return [_summarize(i) for i in instances[:limit]]


def get_object(view: "ReadOnlyStore", instance_id: str) -> dict[str, Any] | None:
    """Fetch one object by id, with its properties, source refs, and resolution (if any)."""
    inst = view.get_instance(instance_id)
    if inst is None:
        return None
    resolution = view.get_resolution(instance_id)
    return {
        **_summarize(inst),
        "properties": inst.properties,
        "source_refs": [
            {"source_key": r.source_key, "external_id": r.external_id} for r in inst.source_refs
        ],
        "resolution": (
            {"confidence": resolution.confidence, "matcher": resolution.matcher}
            if resolution
            else None
        ),
    }


def traverse(
    view: "ReadOnlyStore",
    registry: OntologyRegistry,
    instance_id: str,
    link_type_key: str | None = None,
) -> dict[str, Any]:
    """Follow typed links from an object. Returns neighbors + the link types available from it.

    Link *instances* are not materialized in the pipeline yet (that is a later ontology task), so
    `neighbors` is empty today; the tool still reports which link types *could* be traversed, so the
    agent reasons honestly about the graph rather than inventing edges.
    """
    inst = view.get_instance(instance_id)
    if inst is None:
        return {"instance_id": instance_id, "neighbors": [], "available_link_types": []}
    available = [
        lt.key
        for lt in registry.link_types()
        if lt.from_type == inst.object_type_key
        and (link_type_key is None or lt.key == link_type_key)
    ]
    return {
        "instance_id": instance_id,
        "neighbors": [],  # no LinkInstances materialized yet
        "available_link_types": available,
    }


def run_function(
    view: "ReadOnlyStore",
    registry: OntologyRegistry,
    key: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a registered read-only decision function and return its decisions (no mutation)."""
    fn = registry.get_function(key)
    if fn is None:
        return {
            "error": f"unknown function {key!r}",
            "available": [f.key for f in registry.functions()],
        }
    decisions = fn.run(view, params or {})
    return {
        "function": key,
        "action_needed": sum(1 for d in decisions if d.action_needed),
        "decisions": [d.model_dump() for d in decisions],
    }
