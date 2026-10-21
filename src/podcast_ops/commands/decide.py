"""`decide` command: apply the one read-only rule and report decisions."""

from __future__ import annotations

from podcast_ops.config import Config
from podcast_ops.logic.decision import decide
from podcast_ops.objects.repository import EpisodeRepository


def run_decide(config: Config) -> int:
    """Print episodes the rule selects for action. Returns the count selected."""
    repo = EpisodeRepository(config.objects_dir)
    episodes = repo.load()

    decisions = decide(episodes)
    selected = [d for d in decisions if d.action_needed]

    print(f"Decision rule: apple_without_youtube - {len(selected)}/{len(decisions)} need action")
    for d in selected:
        print(f"  - {d.episode_id}: {d.reason}")
    return len(selected)
