"""Conform — turn a resolved group of staging records into ObjectInstance properties (Principle II).

This is where raw finally becomes an object: it runs only on *resolved* staging records, never on a
raw payload directly. It is domain-agnostic and driven by the ObjectType declaration:

- each declared scalar property is filled from the first contributing source (by the ObjectType's
  `source_bindings` order) whose normalized payload carries that key;
- a declared property named ``<source_key>_ref`` receives that source's compact payload (its per-
  platform reference, e.g. ``youtube_ref`` with engagement counts), so no source-specific wiring
  leaks into the engine — a vertical opts in simply by declaring the property.
"""

from __future__ import annotations

from ontology_engine.ingest.staging import StagingRecord
from ontology_engine.ontology.instances import SourceRef
from ontology_engine.ontology.types import ObjectType

_REF_SUFFIX = "_ref"


def conform(
    object_type: ObjectType, records: list[StagingRecord]
) -> tuple[dict[str, object], list[SourceRef]]:
    """Return (conformed properties, source_refs) for one resolved group of staging records."""
    if not records:
        raise ValueError("conform requires at least one staging record")

    order = {sk: i for i, sk in enumerate(object_type.source_bindings)}
    ordered = sorted(records, key=lambda r: order.get(r.source_key, len(order)))

    properties: dict[str, object] = {}

    # Scalar / non-ref properties: first non-null by source preference.
    for prop_name in object_type.properties:
        if prop_name.endswith(_REF_SUFFIX):
            continue
        for r in ordered:
            value = r.raw_payload.get(prop_name)
            if value is not None:
                properties[prop_name] = value
                break

    # Per-source reference properties (e.g. youtube_ref, apple_ref).
    for r in ordered:
        ref_prop = f"{r.source_key}{_REF_SUFFIX}"
        if ref_prop in object_type.properties:
            ref = {k: v for k, v in r.raw_payload.items() if k != "_raw"}
            ref["external_id"] = r.external_id
            properties[ref_prop] = ref

    source_refs = [SourceRef(source_key=r.source_key, external_id=r.external_id) for r in ordered]
    return properties, source_refs


def embedding_text(object_type: ObjectType, properties: dict[str, object]) -> str:
    """Join the ObjectType's embeddable fields into one text for the embedding provider."""
    parts = [str(properties.get(f, "")) for f in object_type.embeddable_fields]
    return "\n".join(p for p in parts if p).strip()
