"""Integration test: the mock-mode spine makes zero external calls; writeback is safe/logged."""

from pathlib import Path

from podcast_ops.action.writeback import MARKER_PREFIX, YouTubeWriteback
from podcast_ops.commands.act import run_act
from podcast_ops.commands.decide import run_decide
from podcast_ops.commands.fuse import run_fuse
from podcast_ops.config import Config
from podcast_ops.ingest.staging import StagingRepository
from podcast_ops.logic.decision import episodes_needing_action
from podcast_ops.objects.repository import EpisodeRepository


def _config(tmp_path: Path) -> Config:
    return Config(
        youtube_api_key=None,
        youtube_oauth_client_secrets=None,
        youtube_oauth_token=None,
        test_channel_id="UC_test_channel",
        test_video_id="yt_d",
        target_youtube_source=None,
        target_apple_show=None,
        run_dir=tmp_path / "run",
    )


def test_mock_spine_end_to_end(tmp_path, youtube_records, apple_records):
    config = _config(tmp_path)
    # Seed staging directly (ingest transport needs network; mapping already covered).
    staging = StagingRepository(config.staging_dir)
    staging.save("youtube", youtube_records)
    staging.save("apple", apple_records)

    assert run_fuse(config) == 4  # 2 two-sided + 2 one-sided
    assert run_decide(config) == 1  # only the Apple-only episode

    attempts = run_act(config, real=False)  # mock: zero external calls by construction
    assert attempts == 1

    audit = (config.action_dir / "audit.log").read_text(encoding="utf-8").strip().splitlines()
    assert len(audit) == 1
    assert '"mode":"mock"' in audit[0]
    assert '"outcome":"success"' in audit[0]


def test_real_writeback_is_idempotent_and_test_channel_only(
    tmp_path, youtube_records, apple_records
):
    config = _config(tmp_path)
    staging = StagingRepository(config.staging_dir)
    staging.save("youtube", youtube_records)
    staging.save("apple", apple_records)
    run_fuse(config)

    episodes = EpisodeRepository(config.objects_dir).load()
    target = episodes_needing_action(episodes)[0]

    # In-memory fake of an owned test video (dependency injection — no network).
    store = {"channelId": "UC_test_channel", "description": "Original notes."}

    def getter(video_id):
        return dict(store)

    def updater(video_id, new_description):
        store["description"] = new_description

    wb = YouTubeWriteback(
        test_channel_id="UC_test_channel",
        test_video_id="yt_d",
        video_getter=getter,
        video_updater=updater,
    )

    from podcast_ops.logic.decision import decide

    decision = {d.episode_id: d for d in decide(episodes)}[target.episode_id]

    first = wb.publish(decision, target)
    assert first.outcome == "success"
    assert MARKER_PREFIX in store["description"]

    # Retry must not duplicate.
    second = wb.publish(decision, target)
    assert second.outcome == "skipped_idempotent"
    assert store["description"].count(MARKER_PREFIX) == 1


def test_real_writeback_refuses_non_test_channel(tmp_path, youtube_records, apple_records):
    config = _config(tmp_path)
    staging = StagingRepository(config.staging_dir)
    staging.save("youtube", youtube_records)
    staging.save("apple", apple_records)
    run_fuse(config)
    episodes = EpisodeRepository(config.objects_dir).load()
    target = episodes_needing_action(episodes)[0]

    store = {"channelId": "UC_SOMEONE_ELSE", "description": ""}
    wb = YouTubeWriteback(
        test_channel_id="UC_test_channel",
        test_video_id="yt_d",
        video_getter=lambda v: dict(store),
        video_updater=lambda v, d: store.update(description=d),
    )
    from podcast_ops.action.writeback import TargetNotTestChannelError
    from podcast_ops.logic.decision import decide

    decision = {d.episode_id: d for d in decide(episodes)}[target.episode_id]
    import pytest

    with pytest.raises(TargetNotTestChannelError):
        wb.publish(decision, target)
