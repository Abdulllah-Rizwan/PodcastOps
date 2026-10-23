"""Function execution — run a registered read-only function with a ReadOnlyStore only (Principle II).

A `FunctionDef` lives in the `OntologyRegistry` (registered by a vertical). This module is the one
place a function is *executed*: it looks the function up and calls it with `repo.read_view()`, i.e. a
`ReadOnlyStore` that exposes no write method. Read-only-ness is therefore enforced by the handle the
function receives, not by convention — a function literally cannot reach `upsert_instance`,
`record_attempt`, etc. Deciding is not acting (Principle IV).
"""

from __future__ import annotations

from typing import Any

from ontology_engine.functions.definitions import Decision
from ontology_engine.ontology.registry import OntologyRegistry
from ontology_engine.store.repository import Repository


class UnknownFunctionError(KeyError):
    """Raised when a function key is not registered by any vertical."""


def run_function(
    registry: OntologyRegistry,
    repo: Repository,
    key: str,
    params: dict[str, Any] | None = None,
) -> list[Decision]:
    """Execute function `key` read-only and return its decisions. Never mutates the store."""
    fn = registry.get_function(key)
    if fn is None:
        raise UnknownFunctionError(key)
    read_only = repo.read_view()  # ReadOnlyStore: no write methods reachable from here
    return fn.run(read_only, params or {})
