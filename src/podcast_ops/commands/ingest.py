"""`ingest` command: read both platforms into the staging area."""

from __future__ import annotations

from podcast_ops.config import Config
from podcast_ops.ingest.apple_gateway import AppleGateway
from podcast_ops.ingest.staging import StagingRepository
from podcast_ops.ingest.youtube_gateway import YouTubeGateway


def run_ingest(config: Config) -> dict[str, int]:
    """Fetch public metadata from YouTube + Apple Podcasts and persist to staging."""
    if not config.target_youtube_source or not config.target_apple_show:
        raise ValueError("TARGET_YOUTUBE_SOURCE and TARGET_APPLE_SHOW must be set")

    staging = StagingRepository(config.staging_dir)

    yt_gateway = YouTubeGateway(config.youtube_api_key or "")
    ap_gateway = AppleGateway()

    yt_records = yt_gateway.list_episodes(config.target_youtube_source)
    ap_records = ap_gateway.list_episodes(config.target_apple_show)

    staging.save("youtube", yt_records)
    staging.save("apple", ap_records)

    counts = {"youtube": len(yt_records), "apple": len(ap_records)}
    print(f"Ingested -> staging: youtube={counts['youtube']} apple={counts['apple']}")
    return counts
