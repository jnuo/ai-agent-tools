"""OAuth authentication for Google APIs."""

import re
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ..config import get_google_credentials_dir

# Scopes for Calendar and Gmail access
SCOPES = [
    # Calendar
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    # Gmail
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]

# YouTube read + comment-reply + upload. Kept out of SCOPES because the YouTube
# channel is usually owned by a different Google account than Calendar/Gmail, so it
# needs its own token file and its own consent.
#
# force-ssl is a superset that also authorizes videos.insert, so a single consent
# covers reading comments, replying, and uploading.
# https://developers.google.com/youtube/v3/docs/videos/insert#auth
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# Any ONE of these authorizes videos.insert. Checked before an upload so an
# under-scoped token fails with a re-auth instruction instead of a raw 403.
YOUTUBE_UPLOAD_SCOPES = frozenset(
    {
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.force-ssl",
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtubepartner",
    }
)


def youtube_token_filename(account: Optional[str] = None) -> str:
    """Token filename for a YouTube account profile.

    One channel per account profile. The default profile (account=None) keeps the
    historical `token_youtube.json` name; a named profile gets its own token file,
    so several channels (e.g. one per product) can be used side by side.
    """
    if not account:
        return "token_youtube.json"

    safe = re.sub(r"[^A-Za-z0-9_-]", "-", account.strip().lower())
    if not safe.strip("-"):
        raise ValueError(f"Invalid account name: {account!r}")

    return f"token_youtube_{safe}.json"


def _authorize(
    credentials_dir: Path, token_filename: str, scopes: list[str]
) -> Credentials:
    """Load, refresh, or mint credentials for one (token file, scopes) profile."""
    client_secret_file = credentials_dir / "client_secret.json"
    token_file = credentials_dir / token_filename

    creds = None

    # Load existing token if available
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh expired token
            creds.refresh(Request())
        else:
            # Run OAuth flow
            if not client_secret_file.exists():
                raise FileNotFoundError(
                    f"Missing {client_secret_file}\n"
                    "Download OAuth credentials from Google Cloud Console:\n"
                    "1. Go to https://console.cloud.google.com/apis/credentials\n"
                    "2. Create OAuth 2.0 Client ID (Desktop app)\n"
                    "3. Download JSON and save as credentials/google/client_secret.json"
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secret_file), scopes
            )
            creds = flow.run_local_server(port=0)

        # Save token for next run
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return creds


def get_credentials(credentials_dir: Optional[Path] = None) -> Credentials:
    """Get valid credentials, refreshing or re-authenticating as needed.

    Args:
        credentials_dir: Override credentials directory (uses config default if None)

    Returns:
        Valid Google credentials
    """
    if credentials_dir is None:
        credentials_dir = get_google_credentials_dir()

    return _authorize(credentials_dir, "token.json", SCOPES)


def get_youtube_credentials(
    credentials_dir: Optional[Path] = None, account: Optional[str] = None
) -> Credentials:
    """Get valid YouTube credentials (separate account/consent from Gmail/Calendar).

    Args:
        credentials_dir: Override credentials directory (uses config default if None)
        account: Named account profile, to use a channel owned by a different Google
            account (uses the default YouTube token when None)

    Returns:
        Valid Google credentials scoped for YouTube
    """
    if credentials_dir is None:
        credentials_dir = get_google_credentials_dir()

    return _authorize(
        credentials_dir, youtube_token_filename(account), YOUTUBE_SCOPES
    )


def get_calendar_service(credentials_dir: Optional[Path] = None):
    """Get authenticated Calendar API service."""
    creds = get_credentials(credentials_dir)
    return build("calendar", "v3", credentials=creds)


def get_gmail_service(credentials_dir: Optional[Path] = None):
    """Get authenticated Gmail API service."""
    creds = get_credentials(credentials_dir)
    return build("gmail", "v1", credentials=creds)


def get_youtube_service(
    credentials_dir: Optional[Path] = None, account: Optional[str] = None
):
    """Get authenticated YouTube Data API service."""
    creds = get_youtube_credentials(credentials_dir, account=account)
    return build("youtube", "v3", credentials=creds)


def clear_credentials(
    credentials_dir: Optional[Path] = None,
    youtube: bool = False,
    account: Optional[str] = None,
):
    """Remove stored token (for re-authentication).

    Args:
        credentials_dir: Override credentials directory (uses config default if None)
        youtube: Clear the YouTube token instead of the Calendar/Gmail one
        account: Named YouTube account profile to clear (default profile when None)
    """
    if credentials_dir is None:
        credentials_dir = get_google_credentials_dir()

    token_file = credentials_dir / (
        youtube_token_filename(account) if youtube else "token.json"
    )

    if token_file.exists():
        token_file.unlink()
        print(f"Removed {token_file}")
    else:
        print("No stored credentials to clear.")
