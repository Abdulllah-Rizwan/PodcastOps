"""`youtube_update_show_notes` — the vertical #1 writeback action (Principle IV/V).

Appends a show-notes marker to an **owned** test video's description via `videos.update`, linking
the episode's Apple Podcasts counterpart. Safe by construction:

- **owned-target-only**: it refuses to write to any channel but the configured test channel;
- **idempotent**: the marker is appended only if absent (and the engine's `ActionExecutor` also
  skips a repeat of the same idempotency key);
- **access-gated**: `confirm_access` requires an OAuth write token before any real call.

Transport (`videos.get` / `videos.update`) is injected for testability (dependency inversion); in
live use it is bound to the YouTube Data API. Generalized from the slice's `action/writeback.py`.
"""

from __future__ import annotations

from typing import Any, Callable

from ontology_engine.access.check import AccessCheckResult
from ontology_engine.actions.attempt import ActionDef
from ontology_engine.actions.port import ActionOutcome

ACTION_KEY = "youtube_update_show_notes"
SOURCE_KEY = "youtube"
MARKER_PREFIX = "[podcast-ops] linked Apple Podcasts episode:"

# Declarative registration. The idempotency key is (owned video, linked Apple episode).
UPDATE_SHOW_NOTES = ActionDef(
    key=ACTION_KEY,
    description="Append a show-notes marker to an owned test video linking its Apple episode.",
    target=f"{SOURCE_KEY}:test-channel",
    idempotency_key_fields=["test_video_id", "marker_ref"],
    input_schema={
        "test_video_id": {"type": "str", "required": True, "doc": "owned test video id"},
        "marker_ref": {"type": "str", "required": True, "doc": "Apple episode id to link"},
    },
)

# Injected transport signatures:
#   getter(video_id) -> {"channelId": str, "description": str}
#   updater(video_id, new_description) -> None
VideoGetter = Callable[[str], dict[str, Any]]
VideoUpdater = Callable[[str, str], None]


def _marker(marker_ref: str) -> str:
    return f"{MARKER_PREFIX} {marker_ref}"


class UpdateShowNotesHandler:
    """ActionHandler for `youtube_update_show_notes` (owned-target-only, idempotent)."""

    def __init__(
        self,
        *,
        test_channel_id: str | None,
        oauth_token_path: str | None = None,
        getter: VideoGetter | None = None,
        updater: VideoUpdater | None = None,
    ) -> None:
        self._channel = test_channel_id
        self._oauth_token_path = oauth_token_path
        self._get = getter
        self._update = updater

    def describe(self, inputs: dict[str, Any]) -> str:
        return (
            f"append show-notes marker for Apple episode {inputs.get('marker_ref')!r} "
            f"to video {inputs.get('test_video_id')!r}"
        )

    def confirm_access(self) -> AccessCheckResult:
        """Require an owned target and a usable write transport before any real call."""
        if not self._channel:
            return AccessCheckResult(
                source_key=SOURCE_KEY,
                capability="write",
                ok=False,
                detail="missing TEST_CHANNEL_ID",
            )
        if self._get is None or self._update is None:
            return AccessCheckResult(
                source_key=SOURCE_KEY,
                capability="write",
                ok=False,
                detail="no write transport bound (missing YOUTUBE_OAUTH_TOKEN?)",
            )
        return AccessCheckResult(
            source_key=SOURCE_KEY,
            capability="write",
            ok=True,
            detail="ok (owned target + transport)",
        )

    def perform(self, inputs: dict[str, Any]) -> ActionOutcome:
        assert self._get is not None and self._update is not None  # guaranteed by confirm_access
        video_id = str(inputs["test_video_id"])
        marker = _marker(str(inputs["marker_ref"]))

        current = self._get(video_id)
        # Safety: only ever write to our own test channel.
        if current.get("channelId") != self._channel:
            return ActionOutcome(
                status="failed",
                error=(
                    f"refusing to write to channel {current.get('channelId')!r}; "
                    f"only owned test channel {self._channel!r} is allowed"
                ),
            )

        description = current.get("description", "") or ""
        if marker in description:  # target-side idempotency: never duplicate the marker
            return ActionOutcome(
                status="skipped_idempotent", result={"reason": "marker already present"}
            )

        new_description = (description + "\n\n" + marker).strip()
        self._update(video_id, new_description)
        return ActionOutcome(status="success", result={"marker": marker})


def build_handler(settings: Any | None = None) -> UpdateShowNotesHandler:
    """Construct the handler from settings; binds the live YouTube transport when credentials exist.

    With no OAuth token the handler can still `describe` (so preview/mock always works); `perform` is
    unreachable because `confirm_access` fails first.
    """
    if settings is None:
        return UpdateShowNotesHandler(test_channel_id=None)

    getter: VideoGetter | None = None
    updater: VideoUpdater | None = None
    if settings.youtube_oauth_token:  # pragma: no cover - live transport
        getter, updater = _live_transport(settings.youtube_oauth_token)

    return UpdateShowNotesHandler(
        test_channel_id=settings.test_channel_id,
        oauth_token_path=settings.youtube_oauth_token,
        getter=getter,
        updater=updater,
    )


def _live_transport(token_path: str):  # pragma: no cover - requires live OAuth + network
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(token_path)
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)

    def getter(video_id: str) -> dict[str, Any]:
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

    return getter, updater
