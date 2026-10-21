"""LOGIC stage — the one read-only decision rule.

Rule `spotify_without_youtube`: an episode is on Spotify but has no YouTube clip yet. Pure
function over Episode objects; it decides and changes nothing (Principle II).
"""

from __future__ import annotations

from pydantic import BaseModel

from podcast_ops.objects.episode import Episode

RULE_ID = "spotify_without_youtube"


class Decision(BaseModel):
    episode_id: str
    action_needed: bool
    reason: str
    rule: str = RULE_ID


def _decide_one(episode: Episode) -> Decision:
    on_spotify = "spotify" in episode.present_on
    missing_youtube = "youtube" in episode.missing_from
    needed = on_spotify and missing_youtube
    reason = (
        "on Spotify, no YouTube clip yet" if needed else "no action: not a Spotify-only episode"
    )
    return Decision(episode_id=episode.episode_id, action_needed=needed, reason=reason)


def decide(episodes: list[Episode]) -> list[Decision]:
    """Return a Decision for every episode. Read-only: inputs are never mutated."""
    return [_decide_one(e) for e in episodes]


def episodes_needing_action(episodes: list[Episode]) -> list[Episode]:
    """Convenience: the episodes the rule selects for the one action."""
    selected_ids = {d.episode_id for d in decide(episodes) if d.action_needed}
    return [e for e in episodes if e.episode_id in selected_ids]
