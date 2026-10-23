"""The M0 access gate (Principle V), generalized to any source adapter.

The engine stays domain-agnostic: it does not know how to probe YouTube or Apple. Each adapter
implements `confirm_access(capability)` and returns an `AccessCheckResult`; this module just
drives every registered adapter over the capabilities it declares and collects the results.
Modeling/actions against a source require a passing result.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ontology_engine.ingest.adapter import SourceAdapter

AccessCapability = Literal["read", "write"]


class AccessCheckResult(BaseModel):
    """The outcome of one access probe for one (source, capability)."""

    model_config = {"frozen": True}

    source_key: str
    capability: AccessCapability
    ok: bool
    detail: str = ""
    checked_at: datetime = Field(default_factory=datetime.utcnow)


def run_access_checks(adapters: "list[SourceAdapter]") -> list[AccessCheckResult]:
    """Probe every capability each adapter declares; return one result per (source, capability)."""
    results: list[AccessCheckResult] = []
    for adapter in adapters:
        caps = adapter.capabilities()
        for capability in ("read", "write"):
            if caps.supports(capability):  # type: ignore[arg-type]
                results.append(adapter.confirm_access(capability))  # type: ignore[arg-type]
    return results


def all_passed(results: list[AccessCheckResult]) -> bool:
    return bool(results) and all(r.ok for r in results)
