"""Environment-based configuration.

Secrets are read from the process environment (optionally seeded from a local, untracked
`.env` file). Nothing secret is hardcoded here (Principle VI).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: str | os.PathLike[str] = ".env") -> None:
    """Minimal .env loader: `KEY=value` lines seed os.environ if not already set.

    Kept dependency-free on purpose. Existing environment variables win over the file.
    """
    p = Path(path)
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Config:
    """Resolved runtime configuration for one slice run."""

    # Reads
    youtube_api_key: str | None
    spotify_client_id: str | None
    spotify_client_secret: str | None

    # Write (real mode)
    youtube_oauth_client_secrets: str | None
    youtube_oauth_token: str | None
    test_channel_id: str | None
    test_video_id: str | None

    # The one chosen show
    target_youtube_source: str | None
    target_spotify_show: str | None

    # Output
    run_dir: Path

    @classmethod
    def from_env(cls, *, dotenv: bool = True) -> "Config":
        if dotenv:
            load_dotenv()
        return cls(
            youtube_api_key=os.environ.get("YOUTUBE_API_KEY") or None,
            spotify_client_id=os.environ.get("SPOTIFY_CLIENT_ID") or None,
            spotify_client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET") or None,
            youtube_oauth_client_secrets=os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRETS") or None,
            youtube_oauth_token=os.environ.get("YOUTUBE_OAUTH_TOKEN") or None,
            test_channel_id=os.environ.get("TEST_CHANNEL_ID") or None,
            test_video_id=os.environ.get("TEST_VIDEO_ID") or None,
            target_youtube_source=os.environ.get("TARGET_YOUTUBE_SOURCE") or None,
            target_spotify_show=os.environ.get("TARGET_SPOTIFY_SHOW") or None,
            run_dir=Path(os.environ.get("RUN_DIR", "./run")),
        )

    @property
    def staging_dir(self) -> Path:
        return self.run_dir / "staging"

    @property
    def objects_dir(self) -> Path:
        return self.run_dir / "objects"

    @property
    def action_dir(self) -> Path:
        return self.run_dir / "action"
