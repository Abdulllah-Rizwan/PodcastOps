"""Centralized configuration: environment → typed settings (Principle VII).

Nothing secret is hardcoded; values come from the process environment (optionally seeded from a
local, untracked `.env`). In cloud these come from GCP Secret Manager. Generalized from the slice
config to cover storage, embeddings, AI, and tracing alongside the vertical #1 read/write targets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: str | os.PathLike[str] = ".env") -> None:
    """Minimal `.env` loader: `KEY=value` lines seed os.environ if not already set.

    Dependency-free on purpose. Existing environment variables win over the file.
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
class Settings:
    """Resolved runtime configuration for the engine + the registered vertical."""

    # Storage: if database_url is set, Postgres+pgvector; otherwise the JSON backend under run_dir.
    database_url: str | None
    redis_url: str | None
    run_dir: Path

    # Embeddings
    embedding_provider: str  # "local" | "voyage"
    voyage_api_key: str | None

    # AI + tracing
    anthropic_api_key: str | None
    langfuse_host: str | None
    langfuse_public_key: str | None
    langfuse_secret_key: str | None

    # Vertical #1 (podcast) read/write targets — passed to the podcast adapters.
    youtube_api_key: str | None
    youtube_oauth_client_secrets: str | None
    youtube_oauth_token: str | None
    test_channel_id: str | None
    test_video_id: str | None
    target_youtube_source: str | None
    target_apple_show: str | None

    @classmethod
    def from_env(cls, *, dotenv: bool = True) -> "Settings":
        if dotenv:
            load_dotenv()

        def get(name: str) -> str | None:
            return os.environ.get(name) or None

        return cls(
            database_url=get("DATABASE_URL"),
            redis_url=get("REDIS_URL"),
            run_dir=Path(os.environ.get("RUN_DIR", "./run")),
            embedding_provider=os.environ.get("EMBEDDING_PROVIDER", "local"),
            voyage_api_key=get("VOYAGE_API_KEY"),
            anthropic_api_key=get("ANTHROPIC_API_KEY"),
            langfuse_host=get("LANGFUSE_HOST"),
            langfuse_public_key=get("LANGFUSE_PUBLIC_KEY"),
            langfuse_secret_key=get("LANGFUSE_SECRET_KEY"),
            youtube_api_key=get("YOUTUBE_API_KEY"),
            youtube_oauth_client_secrets=get("YOUTUBE_OAUTH_CLIENT_SECRETS"),
            youtube_oauth_token=get("YOUTUBE_OAUTH_TOKEN"),
            test_channel_id=get("TEST_CHANNEL_ID"),
            test_video_id=get("TEST_VIDEO_ID"),
            target_youtube_source=get("TARGET_YOUTUBE_SOURCE"),
            target_apple_show=get("TARGET_APPLE_SHOW"),
        )

    @classmethod
    def empty(
        cls, *, run_dir: str | Path = "./run", embedding_provider: str = "local"
    ) -> "Settings":
        """An all-None config (no DB, no targets, no secrets) for hermetic tests/offline use."""
        return cls(
            database_url=None,
            redis_url=None,
            run_dir=Path(run_dir),
            embedding_provider=embedding_provider,
            voyage_api_key=None,
            anthropic_api_key=None,
            langfuse_host=None,
            langfuse_public_key=None,
            langfuse_secret_key=None,
            youtube_api_key=None,
            youtube_oauth_client_secrets=None,
            youtube_oauth_token=None,
            test_channel_id=None,
            test_video_id=None,
            target_youtube_source=None,
            target_apple_show=None,
        )

    @property
    def use_postgres(self) -> bool:
        return bool(self.database_url)

    @property
    def staging_dir(self) -> Path:
        return self.run_dir / "staging"

    @property
    def store_dir(self) -> Path:
        return self.run_dir / "store"

    @property
    def action_dir(self) -> Path:
        return self.run_dir / "action"
