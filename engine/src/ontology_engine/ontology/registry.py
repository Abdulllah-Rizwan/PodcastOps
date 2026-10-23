"""The vertical registry — the engine's ONLY path to discover a vertical (Principle I).

A `Vertical` bundles what a domain contributes: object types, link types, source adapters,
functions, actions, UI config, and its golden-set location. The engine imports nothing from a
vertical; a vertical calls `OntologyRegistry.register(vertical)` to plug in. This keeps the
engine/vertical seam hard — podcast specifics never leak into the engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ontology_engine.actions.attempt import ActionDef
from ontology_engine.functions.definitions import FunctionDef
from ontology_engine.ingest.adapter import SourceAdapter
from ontology_engine.ontology.types import LinkType, ObjectType


@dataclass(frozen=True)
class Vertical:
    """Everything a domain registers with the engine (a plugin/configuration)."""

    key: str
    object_types: list[ObjectType] = field(default_factory=list)
    link_types: list[LinkType] = field(default_factory=list)
    source_adapters: list[SourceAdapter] = field(default_factory=list)
    function_defs: list[FunctionDef] = field(default_factory=list)
    action_defs: list[ActionDef] = field(default_factory=list)
    ui_config: dict[str, Any] = field(default_factory=dict)
    golden_set_path: str | None = None


class RegistrationError(RuntimeError):
    """Raised when a vertical registration conflicts with what is already registered."""


class OntologyRegistry:
    """Holds the registered verticals and indexes their declarations for lookup."""

    def __init__(self) -> None:
        self._verticals: dict[str, Vertical] = {}
        self._object_types: dict[str, ObjectType] = {}
        self._link_types: dict[str, LinkType] = {}
        self._adapters: dict[str, SourceAdapter] = {}
        self._functions: dict[str, FunctionDef] = {}
        self._actions: dict[str, ActionDef] = {}

    def register(self, vertical: Vertical) -> None:
        if vertical.key in self._verticals:
            raise RegistrationError(f"vertical {vertical.key!r} already registered")

        for ot in vertical.object_types:
            if ot.key in self._object_types:
                raise RegistrationError(f"object type {ot.key!r} already registered")

        for lt in vertical.link_types:
            known = {ot.key for ot in vertical.object_types} | set(self._object_types)
            if lt.from_type not in known or lt.to_type not in known:
                raise RegistrationError(f"link {lt.key!r} references unregistered object type(s)")

        # Commit (only after validation passes, so a failed registration leaves no partial state).
        self._verticals[vertical.key] = vertical
        self._object_types.update({ot.key: ot for ot in vertical.object_types})
        self._link_types.update({lt.key: lt for lt in vertical.link_types})
        self._adapters.update({a.source_key: a for a in vertical.source_adapters})
        self._functions.update({f.key: f for f in vertical.function_defs})
        self._actions.update({a.key: a for a in vertical.action_defs})

    # --- lookups ---------------------------------------------------------

    @property
    def verticals(self) -> list[Vertical]:
        return list(self._verticals.values())

    def object_types(self) -> list[ObjectType]:
        return list(self._object_types.values())

    def get_object_type(self, key: str) -> ObjectType | None:
        return self._object_types.get(key)

    def link_types(self) -> list[LinkType]:
        return list(self._link_types.values())

    def source_adapters(self) -> list[SourceAdapter]:
        return list(self._adapters.values())

    def get_adapter(self, source_key: str) -> SourceAdapter | None:
        return self._adapters.get(source_key)

    def functions(self) -> list[FunctionDef]:
        return list(self._functions.values())

    def get_function(self, key: str) -> FunctionDef | None:
        return self._functions.get(key)

    def actions(self) -> list[ActionDef]:
        return list(self._actions.values())

    def get_action(self, key: str) -> ActionDef | None:
        return self._actions.get(key)
