"""`ingest` command: read both platforms into the staging area."""

from __future__ import annotations

from podcast_ops.config import Config
from podcast_ops.ingest.spotify_gateway import SpotifyGateway
from podcast_ops.ingest.staging import StagingRepository
from podcast_ops.ingest.youtube_gateway import YouTubeGateway


def run_ingest(config: Config) -> dict[str, int]:
    """Fetch public metadata from YouTube + Spotify and persist to staging."""
    if not config.target_youtube_source or not config.target_spotify_show:
        raise ValueError("TARGET_YOUTUBE_SOURCE and TARGET_SPOTIFY_SHOW must be set")

    staging = StagingRepository(config.staging_dir)

    yt_gateway = YouTubeGateway(config.youtube_api_key or "")
    sp_gateway = SpotifyGateway(config.spotify_client_id or "", config.spotify_client_secret or "")

    yt_records = yt_gateway.list_episodes(config.target_youtube_source)
    sp_records = sp_gateway.list_episodes(config.target_spotify_show)

    staging.save("youtube", yt_records)
    staging.save("spotify", sp_records)

    counts = {"youtube": len(yt_records), "spotify": len(sp_records)}
    print(f"Ingested -> staging: youtube={counts['youtube']} spotify={counts['spotify']}")
    return counts
