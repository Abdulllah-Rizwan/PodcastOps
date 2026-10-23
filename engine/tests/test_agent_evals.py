"""T052 — AI agent evals: deterministic, hermetic checks (no API) + the guarded LLM judge.

Builds GroundedAnswers by hand (the live agent loop needs an API key and is out of scope for CI) and
asserts the invariants that make a propose-only grounded agent trustworthy: citations resolve to real
objects, proposed actions are schema/policy valid, and grounded vs ungrounded answers cite
accordingly. The LLM-as-judge is exercised only for its guard (no API key -> raises).
"""

from __future__ import annotations

import pytest

from ontology_engine.ai.agent import Citation, GroundedAnswer
from ontology_engine.ai.propose import ActionProposal
from ontology_engine.evals.agent import evaluate_deterministic, judge_answer
from ontology_engine.ontology.instances import ObjectInstance, SourceRef
from ontology_engine.ontology.registry import OntologyRegistry
from ontology_engine.store.json_repo import JsonRepository
from vertical_podcast.registry import register as register_podcast


@pytest.fixture()
def wired(tmp_path):
    repo = JsonRepository(tmp_path / "store")
    inst = ObjectInstance(
        object_type_key="episode",
        properties={"title": "Apple-only ep", "apple_ref": {"external_id": "a1"}},
        source_refs=[SourceRef(source_key="apple", external_id="a1")],
    )
    repo.upsert_instance(inst)
    registry = OntologyRegistry()
    register_podcast(registry)
    return repo.read_view(), registry, inst.id


def test_grounded_answer_with_real_citation_passes(wired):
    view, registry, instance_id = wired
    answer = GroundedAnswer(
        answer_text="One episode is Apple-only.",
        citations=[Citation(instance_id=instance_id, title="Apple-only ep")],
        trace_id="t1",
        grounded=True,
    )
    report = evaluate_deterministic(answer, view, registry, expect_grounded=True)
    assert report.passed
    assert report.unresolved_citations == []


def test_citation_to_nonexistent_object_fails(wired):
    view, registry, _ = wired
    answer = GroundedAnswer(
        answer_text="See episode xyz.",
        citations=[Citation(instance_id="does-not-exist")],
        trace_id="t2",
        grounded=True,
    )
    report = evaluate_deterministic(answer, view, registry, expect_grounded=True)
    assert not report.passed
    assert report.unresolved_citations == ["does-not-exist"]


def test_invalid_proposed_action_fails(wired):
    view, registry, instance_id = wired
    # Missing required inputs (test_video_id / marker_ref) -> policy/schema invalid.
    answer = GroundedAnswer(
        answer_text="Proposing a writeback.",
        citations=[Citation(instance_id=instance_id)],
        proposed_actions=[ActionProposal(action_key="youtube_update_show_notes", input={})],
        trace_id="t3",
        grounded=True,
    )
    report = evaluate_deterministic(answer, view, registry, expect_grounded=True)
    assert not report.passed
    assert report.invalid_proposals
    assert report.invalid_proposals[0]["action_key"] == "youtube_update_show_notes"


def test_valid_proposed_action_passes(wired):
    view, registry, instance_id = wired
    answer = GroundedAnswer(
        answer_text="Proposing a writeback to the owned test video.",
        citations=[Citation(instance_id=instance_id)],
        proposed_actions=[
            ActionProposal(
                action_key="youtube_update_show_notes",
                input={"test_video_id": "v1", "marker_ref": "a1"},
                valid=True,
            )
        ],
        trace_id="t4",
        grounded=True,
    )
    report = evaluate_deterministic(answer, view, registry, expect_grounded=True)
    assert report.passed


def test_ungrounded_question_expects_no_citations(wired):
    view, registry, _ = wired
    answer = GroundedAnswer(
        answer_text="I have no grounded data for that.",
        citations=[],
        trace_id="t5",
        grounded=False,
    )
    assert evaluate_deterministic(answer, view, registry, expect_grounded=False).passed
    # If we expected grounding, the same answer should fail the grounding check.
    assert not evaluate_deterministic(answer, view, registry, expect_grounded=True).grounding_ok


def test_judge_requires_api_key():
    with pytest.raises(RuntimeError):
        judge_answer("q", "a", "context", api_key=None)
