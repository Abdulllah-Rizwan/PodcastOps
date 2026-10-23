"""T037 — the `apple_without_youtube` decision function (read-only, correct flagging).

Asserts the function flags exactly the Apple-only episodes, that it is handed a *read-only* view
(no write method reachable), and that running it mutates nothing in the store (deciding ≠ acting).
"""

from __future__ import annotations

from ontology_engine.functions.registry import run_function
from ontology_engine.ontology.instances import ObjectInstance, SourceRef
from ontology_engine.ontology.registry import OntologyRegistry
from ontology_engine.store.json_repo import JsonRepository
from vertical_podcast.functions.apple_without_youtube import APPLE_WITHOUT_YOUTUBE, RULE_ID
from vertical_podcast.registry import register as register_podcast


def _episode(*sources: str, title: str) -> ObjectInstance:
    refs = [SourceRef(source_key=s, external_id=f"{s}-{title}") for s in sources]
    return ObjectInstance(object_type_key="episode", properties={"title": title}, source_refs=refs)


def _seed(repo: JsonRepository) -> dict[str, ObjectInstance]:
    apple_only = _episode("apple", title="Apple only")
    fused = _episode("apple", "youtube", title="On both")
    youtube_only = _episode("youtube", title="YouTube only")
    for inst in (apple_only, fused, youtube_only):
        repo.upsert_instance(inst)
    return {"apple_only": apple_only, "fused": fused, "youtube_only": youtube_only}


def test_flags_only_apple_only_episodes(tmp_path):
    repo = JsonRepository(tmp_path / "store")
    seeded = _seed(repo)
    registry = OntologyRegistry()
    register_podcast(registry)

    decisions = run_function(registry, repo, RULE_ID)
    flagged = {d.instance_id for d in decisions if d.action_needed}

    assert flagged == {seeded["apple_only"].id}
    assert {d.rule for d in decisions} == {RULE_ID}


def test_function_receives_read_only_view_and_writes_nothing(tmp_path):
    repo = JsonRepository(tmp_path / "store")
    _seed(repo)
    before = {i.id for i in repo.query_instances("episode", limit=100)}

    # The function is handed read_view(): a ReadOnlyStore that exposes no write methods at all.
    view = repo.read_view()
    assert not hasattr(view, "upsert_instance")
    assert not hasattr(view, "record_attempt")
    assert not hasattr(view, "save_resolution")

    APPLE_WITHOUT_YOUTUBE.run(view, {})

    after = {i.id for i in repo.query_instances("episode", limit=100)}
    assert after == before  # deciding changed nothing
    assert repo.list_attempts() == []  # and recorded no action
