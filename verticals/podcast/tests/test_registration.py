"""M0 smoke tests: the podcast vertical registers its types, links, and sources on the engine,
through the registry only (Principle I — no engine import of the vertical)."""

from __future__ import annotations

from ontology_engine.ontology.registry import OntologyRegistry
from vertical_podcast.registry import VERTICAL_KEY, build_vertical, register


def test_build_vertical_declares_expected_types() -> None:
    vertical = build_vertical()
    assert vertical.key == VERTICAL_KEY
    assert {ot.key for ot in vertical.object_types} == {"show", "episode", "guest", "clip"}
    assert {lt.key for lt in vertical.link_types} == {"belongsTo", "features", "hasClip"}
    assert {a.source_key for a in vertical.source_adapters} == {"youtube", "apple"}


def test_register_plugs_into_engine_registry() -> None:
    reg = OntologyRegistry()
    register(reg)
    assert reg.get_object_type("episode") is not None
    assert reg.get_adapter("youtube") is not None
    assert reg.get_adapter("apple") is not None
    # Episode is the fusion target and binds both sources.
    episode = reg.get_object_type("episode")
    assert set(episode.source_bindings) == {"youtube", "apple"}


def test_source_capabilities() -> None:
    vertical = build_vertical()
    caps = {a.source_key: a.capabilities() for a in vertical.source_adapters}
    assert caps["youtube"].read and caps["youtube"].write
    assert caps["apple"].read and not caps["apple"].write
