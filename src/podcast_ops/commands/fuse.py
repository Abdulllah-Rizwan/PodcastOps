"""`fuse` command: resolve + conform staged records into Episode objects."""

from __future__ import annotations

from podcast_ops.config import Config
from podcast_ops.ingest.staging import StagingRepository
from podcast_ops.objects.repository import EpisodeRepository
from podcast_ops.resolve.conform import conform
from podcast_ops.resolve.matcher import Matcher


def run_fuse(config: Config) -> int:
    """Build fused Episode objects from staging and persist them. Returns episode count."""
    staging = StagingRepository(config.staging_dir)
    youtube = staging.load("youtube")
    apple = staging.load("apple")

    episodes = conform(youtube, apple, matcher=Matcher())

    repo = EpisodeRepository(config.objects_dir)
    repo.save(episodes)

    two_sided = sum(1 for e in episodes if e.is_two_sided)
    print(
        f"Fused {len(episodes)} Episode objects "
        f"({two_sided} two-sided, {len(episodes) - two_sided} one-sided) -> {repo.path}"
    )
    return len(episodes)
