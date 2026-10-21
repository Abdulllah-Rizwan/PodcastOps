"""ACTION stage — the one writeback, behind a seam.

`WritebackPort` is the interface; `MockWriteback` logs "would publish X to Y" and makes no
external call; `YouTubeWriteback` performs the real `videos.update` against our own test channel.
Safe (idempotent/retryable), test-channel-only, and logged (Principle IV).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Literal, Optional, Protocol

from pydantic import BaseModel

from podcast_ops.logic.decision import Decision
from podcast_ops.objects.episode import Episode

logger = logging.getLogger("podcast_ops.action")

# Marker appended to a test video's description so retries are idempotent.
MARKER_PREFIX = "[podcast-ops] linked Spotify episode:"


class WritebackAttempt(BaseModel):
    attempt_id: str
    episode_id: str
    mode: Literal["mock", "real"]
    target: str
    intended_change: str
    outcome: Literal["success", "failure", "skipped_idempotent"]
    error: Optional[str] = None
    timestamp: datetime


def _new_attempt(
    episode: Episode,
    mode: str,
    target: str,
    intended_change: str,
    outcome: str,
    error: str | None = None,
) -> WritebackAttempt:
    return WritebackAttempt(
        attempt_id=uuid.uuid4().hex,
        episode_id=episode.episode_id,
        mode=mode,  # type: ignore[arg-type]
        target=target,
        intended_change=intended_change,
        outcome=outcome,  # type: ignore[arg-type]
        error=error,
        timestamp=datetime.utcnow(),
    )


def _intended_change(episode: Episode) -> str:
    sp = episode.spotify
    sp_url = sp.url if sp else None
    return (
        f"append show-notes marker for Spotify episode {sp.platform_id if sp else '?'} ({sp_url})"
    )


class WritebackPort(Protocol):
    def publish(self, decision: Decision, episode: Episode) -> WritebackAttempt:
        ...


class MockWriteback:
    """Default. Logs the intended writeback; makes no external call."""

    def __init__(self, target: str = "mock://test-channel") -> None:
        self._target = target

    def publish(self, decision: Decision, episode: Episode) -> WritebackAttempt:
        change = _intended_change(episode)
        logger.info('would publish "%s" to %s', change, self._target)
        return _new_attempt(episode, "mock", self._target, change, "success")


class TargetNotTestChannelError(RuntimeError):
    """Raised if a real writeback is aimed at anything but the configured test channel."""


class YouTubeWriteback:
    """Real writeback: updates an owned test video's description. Test-channel-only.

    `video_getter`/`video_updater` are injected for testability (dependency inversion). In live
    use they are bound to the YouTube Data API client.
    """

    def __init__(
        self,
        *,
        test_channel_id: str,
        test_video_id: str,
        video_getter,
        video_updater,
    ) -> None:
        if not test_channel_id or not test_video_id:
            raise ValueError("test channel id and test video id are required for real writeback")
        self._channel = test_channel_id
        self._video = test_video_id
        self._get = video_getter  # (video_id) -> {"channelId","description"}
        self._update = video_updater  # (video_id, new_description) -> None

    def publish(self, decision: Decision, episode: Episode) -> WritebackAttempt:
        change = _intended_change(episode)
        target = f"youtube:{self._video}"
        try:
            current = self._get(self._video)

            # Safety: only ever write to our own test channel.
            if current.get("channelId") != self._channel:
                raise TargetNotTestChannelError(
                    f"refusing to write to {current.get('channelId')}; "
                    f"only test channel {self._channel} is allowed"
                )

            marker = f"{MARKER_PREFIX} {episode.spotify.platform_id if episode.spotify else ''}"
            description = current.get("description", "") or ""

            # Idempotency: do not duplicate on retry.
            if marker in description:
                return _new_attempt(episode, "real", target, change, "skipped_idempotent")

            new_description = (description + "\n\n" + marker).strip()
            self._update(self._video, new_description)
            return _new_attempt(episode, "real", target, change, "success")
        except TargetNotTestChannelError:
            raise
        except Exception as exc:  # safe: failure is logged and retryable
            return _new_attempt(episode, "real", target, change, "failure", error=str(exc))
