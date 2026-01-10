"""OAuth authentication for Google APIs."""

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


def get_credentials(credentials_dir: Optional[Path] = None) -> Credentials:
    """Get valid credentials, refreshing or re-authenticating as needed.

    Args:
        credentials_dir: Override credentials directory (uses config default if None)

    Returns:
        Valid Google credentials
    """
    if credentials_dir is None:
        credentials_dir = get_google_credentials_dir()

    client_secret_file = credentials_dir / "client_secret.json"
    token_file = credentials_dir / "token.json"

    creds = None

    # Load existing token if available
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

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
                str(client_secret_file), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token for next run
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return creds


def get_calendar_service(credentials_dir: Optional[Path] = None):
    """Get authenticated Calendar API service."""
    creds = get_credentials(credentials_dir)
    return build("calendar", "v3", credentials=creds)


def get_gmail_service(credentials_dir: Optional[Path] = None):
    """Get authenticated Gmail API service."""
    creds = get_credentials(credentials_dir)
    return build("gmail", "v1", credentials=creds)


def clear_credentials(credentials_dir: Optional[Path] = None):
    """Remove stored token (for re-authentication)."""
    if credentials_dir is None:
        credentials_dir = get_google_credentials_dir()

    token_file = credentials_dir / "token.json"

    if token_file.exists():
        token_file.unlink()
        print(f"Removed {token_file}")
    else:
        print("No stored credentials to clear.")
