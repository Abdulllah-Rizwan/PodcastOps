"""T066 (vertical side) — owned-target-only is enforced by the handler itself.

The `youtube_update_show_notes` action must refuse to write to any channel but the configured
owned test channel, even if every other gate (approval, access, idempotency) has passed. This test
drives the handler's `perform` directly with an injected transport that reports a *foreign* channel
and asserts the write is refused.
"""

from __future__ import annotations

from vertical_podcast.actions.update_show_notes import UpdateShowNotesHandler

OWNED = "UC_owned_test_channel"
FOREIGN = "UC_someone_elses_channel"


def _handler(channel_of_video: str) -> UpdateShowNotesHandler:
    """A handler whose injected transport reports `channel_of_video` for any video."""
    updated: list[tuple[str, str]] = []

    def getter(video_id: str) -> dict:
        return {"channelId": channel_of_video, "description": "existing notes"}

    def updater(video_id: str, new_description: str) -> None:
        updated.append((video_id, new_description))

    handler = UpdateShowNotesHandler(test_channel_id=OWNED, getter=getter, updater=updater)
    handler._updated = updated  # type: ignore[attr-defined]  # expose for assertion
    return handler


def test_refuses_to_write_to_a_foreign_channel() -> None:
    handler = _handler(channel_of_video=FOREIGN)
    outcome = handler.perform({"test_video_id": "v1", "marker_ref": "a1"})
    assert outcome.status == "failed"
    assert "refusing to write" in (outcome.error or "")
    assert handler._updated == []  # type: ignore[attr-defined]  # nothing was written


def test_writes_to_the_owned_channel() -> None:
    handler = _handler(channel_of_video=OWNED)
    outcome = handler.perform({"test_video_id": "v1", "marker_ref": "a1"})
    assert outcome.status == "success"
    assert handler._updated and handler._updated[0][0] == "v1"  # type: ignore[attr-defined]


def test_confirm_access_requires_an_owned_target() -> None:
    # No channel configured -> access must not be confirmed (nothing to own).
    handler = UpdateShowNotesHandler(test_channel_id=None)
    assert handler.confirm_access().ok is False
