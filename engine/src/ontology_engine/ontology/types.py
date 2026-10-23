"""ObjectType and LinkType — the declarative schema of an ontology (Principle II).

A vertical declares these and registers them with the engine; the engine itself carries no
domain-specific types. `ObjectType` ≈ a table, `LinkType` ≈ a typed, directional relationship
between two object types.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Cardinality = Literal["one", "many"]


class PropertySpec(BaseModel):
    """One typed, validated field on an object type."""

    model_config = {"frozen": True}

    type: str  # logical type name, e.g. "str", "int", "date", "datetime", "float", "json"
    required: bool = False
    # An identifying property participates in resolution blocking (candidate generation).
    identifying: bool = False
    format: str | None = None
    description: str | None = None


class ObjectType(BaseModel):
    """The declared kind of thing in an ontology."""

    model_config = {"frozen": True}

    key: str  # unique within an ontology, e.g. "episode"
    description: str | None = None
    properties: dict[str, PropertySpec] = Field(default_factory=dict)
    # Which properties feed the embedding (e.g. title, description).
    embeddable_fields: list[str] = Field(default_factory=list)
    # Source adapter keys that may contribute to this type (e.g. ["youtube", "apple"]).
    source_bindings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> "ObjectType":
        if not self.key:
            raise ValueError("ObjectType.key is required")
        for field in self.embeddable_fields:
            if field not in self.properties:
                raise ValueError(f"embeddable field {field!r} is not a declared property")
        return self

    @property
    def identifying_fields(self) -> list[str]:
        return [name for name, spec in self.properties.items() if spec.identifying]


class LinkType(BaseModel):
    """A typed, directional relationship between two object types."""

    model_config = {"frozen": True}

    key: str  # e.g. "features", "hasClip", "belongsTo"
    from_type: str  # ObjectType.key
    to_type: str  # ObjectType.key
    cardinality: Cardinality = "many"
    description: str | None = None

    @model_validator(mode="after")
    def _check(self) -> "LinkType":
        if not (self.key and self.from_type and self.to_type):
            raise ValueError("LinkType requires key, from_type, and to_type")
        return self
