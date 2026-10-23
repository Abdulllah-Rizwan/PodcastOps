"""Ontology explorer endpoints (US1, T034) — read-only views of the fused ontology.

Surfaces object types, instances (with a fused flag + resolution summary), one instance's detail
with linked instances, the full ResolutionDecision (signals + confidence + rejected candidate), and
the registered link types for graph traversal. All GET, all side-effect-free.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.state import AppContext, get_ctx
from ontology_engine.ontology.instances import ObjectInstance
from ontology_engine.ontology.types import ObjectType

router = APIRouter(tags=["ontology"])


def _type_dict(ot: ObjectType, ctx: AppContext) -> dict[str, object]:
    links = [
        {"key": lt.key, "from": lt.from_type, "to": lt.to_type, "cardinality": lt.cardinality}
        for lt in ctx.registry.link_types()
        if lt.from_type == ot.key or lt.to_type == ot.key
    ]
    return {
        "key": ot.key,
        "description": ot.description,
        "properties": {
            name: {"type": spec.type, "required": spec.required, "identifying": spec.identifying}
            for name, spec in ot.properties.items()
        },
        "embeddable_fields": ot.embeddable_fields,
        "source_bindings": ot.source_bindings,
        "links": links,
    }


def _resolution_summary(ctx: AppContext, instance: ObjectInstance) -> dict[str, object] | None:
    decision = ctx.repo.get_resolution(instance.id)
    if decision is None:
        return None
    return {"confidence": decision.confidence, "matcher": decision.matcher}


def _instance_dict(ctx: AppContext, inst: ObjectInstance) -> dict[str, object]:
    return {
        "id": inst.id,
        "object_type_key": inst.object_type_key,
        "properties": inst.properties,
        "source_refs": [r.model_dump(mode="json") for r in inst.source_refs],
        "is_fused": inst.is_fused,
        "resolution": _resolution_summary(ctx, inst),
    }


@router.get("/ontology/types")
def list_types(ctx: AppContext = Depends(get_ctx)) -> dict[str, object]:
    return {"types": [_type_dict(ot, ctx) for ot in ctx.registry.object_types()]}


@router.get("/ontology/types/{key}/instances")
def list_instances(
    key: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    source: str | None = None,
    fused: bool | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> dict[str, object]:
    if ctx.registry.get_object_type(key) is None:
        raise HTTPException(status_code=404, detail=f"unknown object type {key!r}")
    filters: dict[str, object] = {}
    if source is not None:
        filters["source"] = source
    if fused is not None:
        filters["fused"] = fused
    items = ctx.repo.query_instances(key, filters, limit=limit, offset=offset)
    return {
        "items": [_instance_dict(ctx, i) for i in items],
        "limit": limit,
        "offset": offset,
        "count": len(items),
    }


@router.get("/ontology/instances/{instance_id}")
def get_instance(instance_id: str, ctx: AppContext = Depends(get_ctx)) -> dict[str, object]:
    inst = ctx.repo.get_instance(instance_id)
    if inst is None:
        raise HTTPException(status_code=404, detail=f"instance {instance_id} not found")
    data = _instance_dict(ctx, inst)
    data["linked"] = []  # link instances are populated in a later phase (guest/clip extraction)
    return data


@router.get("/ontology/instances/{instance_id}/resolution")
def get_resolution(instance_id: str, ctx: AppContext = Depends(get_ctx)) -> dict[str, object]:
    if ctx.repo.get_instance(instance_id) is None:
        raise HTTPException(status_code=404, detail=f"instance {instance_id} not found")
    decision = ctx.repo.get_resolution(instance_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="no resolution decision for this instance")
    return decision.model_dump(mode="json")


@router.get("/ontology/links")
def list_links(ctx: AppContext = Depends(get_ctx)) -> dict[str, object]:
    return {
        "link_types": [
            {"key": lt.key, "from": lt.from_type, "to": lt.to_type, "cardinality": lt.cardinality}
            for lt in ctx.registry.link_types()
        ]
    }
