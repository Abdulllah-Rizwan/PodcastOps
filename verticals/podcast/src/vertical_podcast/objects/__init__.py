"""Podcast object types + link types, declared against the engine's ontology model."""

from __future__ import annotations

from vertical_podcast.objects.types import (
    EPISODE,
    EPISODE_HAS_CLIP,
    EPISODE_FEATURES_GUEST,
    EPISODE_BELONGS_TO_SHOW,
    CLIP,
    GUEST,
    SHOW,
    LINK_TYPES,
    OBJECT_TYPES,
)

__all__ = [
    "SHOW",
    "EPISODE",
    "GUEST",
    "CLIP",
    "EPISODE_BELONGS_TO_SHOW",
    "EPISODE_FEATURES_GUEST",
    "EPISODE_HAS_CLIP",
    "OBJECT_TYPES",
    "LINK_TYPES",
]
