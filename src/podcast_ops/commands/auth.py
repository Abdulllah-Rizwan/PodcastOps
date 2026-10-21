"""`auth` command: one-time OAuth consent that mints the YouTube write token.

Runs the installed-app (desktop) OAuth flow against your downloaded client-secrets file,
opens a browser for consent (log in as the test-channel owner), and saves the authorized
token to YOUTUBE_OAUTH_TOKEN. Needed only for the real writeback; reads never use it.
"""

from __future__ import annotations

from pathlib import Path

from podcast_ops.config import Config

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
DEFAULT_TOKEN_PATH = "./secrets/youtube_token.json"


def run_auth(config: Config, *, port: int = 8888) -> int:
    if not config.youtube_oauth_client_secrets:
        raise ValueError(
            "YOUTUBE_OAUTH_CLIENT_SECRETS must point to your downloaded OAuth client JSON"
        )
    client_secrets = Path(config.youtube_oauth_client_secrets)
    if not client_secrets.exists():
        raise FileNotFoundError(f"OAuth client secrets not found: {client_secrets}")

    # Lazy import: part of the optional [live] extra.
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
    print(f"Opening browser for consent (local redirect on port {port})...")
    print("Log in as the account that OWNS your throwaway test channel, then approve.")
    creds = flow.run_local_server(port=port, prompt="consent")

    token_path = Path(config.youtube_oauth_token or DEFAULT_TOKEN_PATH)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")

    print(f"Saved YouTube OAuth token -> {token_path}")
    print("Granted scopes: " + " ".join(creds.scopes or []))
    print("Next: run `podcast-ops check-access` to confirm the write probe is OK.")
    return 0
