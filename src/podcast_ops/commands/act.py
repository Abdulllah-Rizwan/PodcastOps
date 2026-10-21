"""`act` command: execute the one writeback (mock by default, real on request)."""

from __future__ import annotations

from podcast_ops.action.audit_log import AuditLog
from podcast_ops.action.writeback import MockWriteback, WritebackPort, YouTubeWriteback
from podcast_ops.config import Config
from podcast_ops.logic.decision import decide, episodes_needing_action
from podcast_ops.objects.repository import EpisodeRepository


def _build_real_writeback(config: Config) -> YouTubeWriteback:  # pragma: no cover - live
    """Bind a real YouTube writeback to the Data API client (test channel only)."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(config.youtube_oauth_token)
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)

    def getter(video_id: str) -> dict:
        resp = yt.videos().list(part="snippet", id=video_id).execute()
        items = resp.get("items", [])
        if not items:
            raise RuntimeError(f"video {video_id} not found")
        snippet = items[0]["snippet"]
        return {
            "channelId": snippet.get("channelId"),
            "description": snippet.get("description", ""),
        }

    def updater(video_id: str, new_description: str) -> None:
        resp = yt.videos().list(part="snippet", id=video_id).execute()
        snippet = resp["items"][0]["snippet"]
        snippet["description"] = new_description
        yt.videos().update(part="snippet", body={"id": video_id, "snippet": snippet}).execute()

    return YouTubeWriteback(
        test_channel_id=config.test_channel_id or "",
        test_video_id=config.test_video_id or "",
        video_getter=getter,
        video_updater=updater,
    )


def run_act(config: Config, *, real: bool = False) -> int:
    """Run the writeback for each selected episode. Returns number of attempts."""
    repo = EpisodeRepository(config.objects_dir)
    episodes = repo.load()
    targets = episodes_needing_action(episodes)

    port: WritebackPort = _build_real_writeback(config) if real else MockWriteback()
    audit = AuditLog(config.action_dir)

    decisions = {d.episode_id: d for d in decide(episodes)}
    attempts = 0
    for ep in targets:
        attempt = port.publish(decisions[ep.episode_id], ep)
        audit.record(attempt)
        attempts += 1
        print(f"  [{attempt.mode}] {ep.episode_id}: {attempt.outcome}")

    mode = "real" if real else "mock"
    print(f"Action ({mode}): {attempts} writeback attempt(s), logged to {audit.path}")
    return attempts
