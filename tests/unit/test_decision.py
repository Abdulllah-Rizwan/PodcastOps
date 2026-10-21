"""Unit tests for the one decision rule (read-only, Principle II)."""

from podcast_ops.logic.decision import decide, episodes_needing_action
from podcast_ops.resolve.conform import conform


def _episodes(youtube_records, apple_records):
    return conform(youtube_records, apple_records)


def test_selects_only_apple_without_youtube(youtube_records, apple_records):
    episodes = _episodes(youtube_records, apple_records)
    selected = episodes_needing_action(episodes)
    # Only the Apple-only episode (ap_c / "Deep Sea Mysteries") should be selected.
    assert len(selected) == 1
    ep = selected[0]
    assert ep.apple is not None and ep.apple.platform_id == "ap_c"
    assert ep.youtube is None
    assert "youtube" in ep.missing_from


def test_two_sided_and_youtube_only_not_selected(youtube_records, apple_records):
    episodes = _episodes(youtube_records, apple_records)
    decisions = {d.episode_id: d for d in decide(episodes)}
    for ep in episodes:
        if ep.is_two_sided or (ep.youtube and not ep.apple):
            assert decisions[ep.episode_id].action_needed is False


def test_rule_is_read_only(youtube_records, apple_records):
    episodes = _episodes(youtube_records, apple_records)
    before = [e.model_dump() for e in episodes]
    decide(episodes)
    after = [e.model_dump() for e in episodes]
    assert before == after
