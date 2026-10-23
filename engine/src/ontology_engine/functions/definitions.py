"""FunctionDef — a declarative, read-only computation over objects (Principle II).

A function decides ("what should we do?") and changes nothing. It is given a `ReadOnlyStore` and
returns a list of `Decision`s. The engine enforces read-only-ness by the handle it passes (there is
no writable repository method reachable from a `ReadOnlyStore`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ontology_engine.store.repository import ReadOnlyStore


class Decision(BaseModel):
    """One read-only decision about one object instance."""

    instance_id: str
    action_needed: bool
    reason: str
    rule: str
    detail: dict[str, Any] = Field(default_factory=dict)


# A function reads the world through a ReadOnlyStore and returns decisions. It MUST NOT mutate.
FunctionRunner = Callable[["ReadOnlyStore", dict[str, Any]], list[Decision]]


class FunctionDef(BaseModel):
    """A registered read-only function."""

    model_config = {"arbitrary_types_allowed": True, "frozen": True}

    key: str
    description: str = ""
    # Which object types the function reads (for documentation / UI).
    input_types: list[str] = Field(default_factory=list)
    # Typed as FunctionRunner for callers; annotated loosely here so pydantic need not resolve the
    # TYPE_CHECKING-only `ReadOnlyStore` forward ref in the Callable signature.
    run: Callable[..., list[Decision]]
