"""Authentication for analytics APIs.

Supports two modes:
1. OAuth (interactive) — uses client_secret.json, stores token_analytics.json
2. Service account (CI/automated) — GA4_SERVICE_ACCOUNT_JSON env var or GA4_SERVICE_ACCOUNT_FILE
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from ..config import get_google_credentials_dir

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


def get_ga4_credentials():
    """Get GA4 credentials — service account first, then OAuth fallback.

    Priority:
    1. GA4_SERVICE_ACCOUNT_JSON env var (JSON string — for CI)
    2. GA4_SERVICE_ACCOUNT_FILE env var (path to JSON file)
    3. OAuth flow (interactive — uses client_secret.json)

    Returns:
        google.auth.credentials.Credentials
    """
    # 1. Service account from env var (JSON string)
    sa_json = os.environ.get("GA4_SERVICE_ACCOUNT_JSON")
    if sa_json:
        from google.oauth2 import service_account
        info = json.loads(sa_json)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

    # 2. Service account from file path
    sa_file = os.environ.get("GA4_SERVICE_ACCOUNT_FILE")
    if sa_file and Path(sa_file).exists():
        from google.oauth2 import service_account
        return service_account.Credentials.from_service_account_file(sa_file, scopes=SCOPES)

    # 3. OAuth flow (interactive)
    return _get_oauth_credentials()


def _get_oauth_credentials():
    """Get OAuth credentials for interactive use."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    credentials_dir = get_google_credentials_dir()
    client_secret_file = credentials_dir / "client_secret.json"
    token_file = credentials_dir / "token_analytics.json"

    creds = None

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secret_file.exists():
                raise FileNotFoundError(
                    f"Missing {client_secret_file}\n"
                    "Download OAuth credentials from Google Cloud Console:\n"
                    "1. Go to https://console.cloud.google.com/apis/credentials\n"
                    "2. Create OAuth 2.0 Client ID (Desktop app)\n"
                    "3. Download JSON and save as credentials/google/client_secret.json"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secret_file), SCOPES
            )
            creds = flow.run_local_server(port=0)

        token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return creds


def run_gh_api(endpoint: str) -> dict | list:
    """Run a GitHub API call via gh CLI.

    Args:
        endpoint: API endpoint (e.g., 'repos/owner/repo')

    Returns:
        Parsed JSON response
    """
    result = subprocess.run(
        ["gh", "api", endpoint],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh api failed: {result.stderr.strip()}")
    return json.loads(result.stdout)
