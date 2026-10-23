"""Podcast ObjectTypes and LinkTypes (vertical #1).

`Episode` is the fusion target — the same real-world episode matched across YouTube and Apple
Podcasts into one instance (Principle III). These are plain engine `ObjectType`/`LinkType`
declarations; the engine stays domain-agnostic and learns about them only via registration.
"""

from __future__ import annotations

from ontology_engine.ontology.types import LinkType, ObjectType, PropertySpec

SHOW = ObjectType(
    key="show",
    description="A podcast show / channel.",
    properties={
        "title": PropertySpec(type="str", required=True, identifying=True),
        "description": PropertySpec(type="str"),
        "publisher": PropertySpec(type="str"),
        "youtube_channel_id": PropertySpec(type="str"),
        "apple_collection_id": PropertySpec(type="str"),
    },
    embeddable_fields=["title", "description"],
    source_bindings=["youtube", "apple"],
)

EPISODE = ObjectType(
    key="episode",
    description="One real-world episode, fused across platforms.",
    properties={
        "title": PropertySpec(type="str", required=True, identifying=True),
        "description": PropertySpec(type="str"),
        "published_at": PropertySpec(type="date", required=True, identifying=True),
        "duration_s": PropertySpec(type="int", identifying=True),
        # Per-platform references. youtube_ref carries public engagement counts; apple_ref the ids.
        "youtube_ref": PropertySpec(type="json"),
        "apple_ref": PropertySpec(type="json"),
    },
    embeddable_fields=["title", "description"],
    source_bindings=["youtube", "apple"],
)

GUEST = ObjectType(
    key="guest",
    description="A person featured in an episode.",
    properties={
        "name": PropertySpec(type="str", required=True, identifying=True),
        "aliases": PropertySpec(type="json"),
    },
    embeddable_fields=["name"],
    source_bindings=["youtube", "apple"],
)

CLIP = ObjectType(
    key="clip",
    description="A short clip derived from an episode (e.g. a YouTube short).",
    properties={
        "title": PropertySpec(type="str", required=True),
        "youtube_video_id": PropertySpec(type="str", identifying=True),
        "parent_episode_ref": PropertySpec(type="str"),
    },
    embeddable_fields=["title"],
    source_bindings=["youtube"],
)

EPISODE_BELONGS_TO_SHOW = LinkType(
    key="belongsTo", from_type="episode", to_type="show", cardinality="one"
)
EPISODE_FEATURES_GUEST = LinkType(
    key="features", from_type="episode", to_type="guest", cardinality="many"
)
EPISODE_HAS_CLIP = LinkType(key="hasClip", from_type="episode", to_type="clip", cardinality="many")

OBJECT_TYPES = [SHOW, EPISODE, GUEST, CLIP]
LINK_TYPES = [EPISODE_BELONGS_TO_SHOW, EPISODE_FEATURES_GUEST, EPISODE_HAS_CLIP]
