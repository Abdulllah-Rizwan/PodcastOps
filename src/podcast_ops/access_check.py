"""M0 access gate (Principle V): confirm the one read and the one write are permitted.

Each probe returns (ok, message). With credentials absent it reports what is missing; with
credentials present it makes a minimal live call. Running all three green is the gate that must
pass before modeling against real data proceeds.
"""

from __future__ import annotations

from dataclasses import dataclass

from podcast_ops.config import Config


@dataclass(frozen=True)
class ProbeResult:
    name: str
    ok: bool
    message: str


def check_youtube_read(config: Config) -> ProbeResult:  # pragma: no cover - live
    name = "YouTube read (API key)"
    if not config.youtube_api_key:
        return ProbeResult(name, False, "missing YOUTUBE_API_KEY")
    if not config.target_youtube_source:
        return ProbeResult(name, False, "missing TARGET_YOUTUBE_SOURCE")
    try:
        from googleapiclient.discovery import build

        yt = build("youtube", "v3", developerKey=config.youtube_api_key, cache_discovery=False)
        yt.channels().list(part="id", id=config.target_youtube_source).execute()
        return ProbeResult(name, True, "ok")
    except Exception as exc:
        return ProbeResult(name, False, f"error: {exc}")


def check_spotify_read(config: Config) -> ProbeResult:  # pragma: no cover - live
    name = "Spotify read (client credentials)"
    if not (config.spotify_client_id and config.spotify_client_secret):
        return ProbeResult(name, False, "missing SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET")
    if not config.target_spotify_show:
        return ProbeResult(name, False, "missing TARGET_SPOTIFY_SHOW")
    try:
        import httpx

        tok = httpx.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(config.spotify_client_id, config.spotify_client_secret),
            timeout=30,
        )
        tok.raise_for_status()
        token = tok.json()["access_token"]
        resp = httpx.get(
            f"https://api.spotify.com/v1/shows/{config.target_spotify_show}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        resp.raise_for_status()
        return ProbeResult(name, True, "ok")
    except Exception as exc:
        return ProbeResult(name, False, f"error: {exc}")


def check_youtube_write(config: Config) -> ProbeResult:  # pragma: no cover - live
    name = "YouTube write (OAuth, test channel)"
    if not config.youtube_oauth_token:
        return ProbeResult(name, False, "missing YOUTUBE_OAUTH_TOKEN (run OAuth consent first)")
    if not (config.test_channel_id and config.test_video_id):
        return ProbeResult(name, False, "missing TEST_CHANNEL_ID / TEST_VIDEO_ID")
    try:
        from google.oauth2.credentials import Credentials

        creds = Credentials.from_authorized_user_file(config.youtube_oauth_token)
        scopes = set(creds.scopes or [])
        if "https://www.googleapis.com/auth/youtube.force-ssl" not in scopes:
            return ProbeResult(name, False, "token lacks scope youtube.force-ssl")
        return ProbeResult(name, True, "ok (write scope present)")
    except Exception as exc:
        return ProbeResult(name, False, f"error: {exc}")


def run_all(config: Config) -> list[ProbeResult]:
    return [check_youtube_read(config), check_spotify_read(config), check_youtube_write(config)]
