"""Resend API authentication."""

from typing import Optional

import requests

from ..config import get_resend_api_key

# Resend API base URL
RESEND_API_BASE = "https://api.resend.com"


class ResendAuthError(Exception):
    """Raised when Resend authentication fails."""
    pass


def get_headers(api_key: Optional[str] = None) -> dict:
    """Get headers for Resend API requests.

    Args:
        api_key: Override API key (uses config default if None)

    Returns:
        Headers dict for requests

    Raises:
        ResendAuthError: If no API key found
    """
    key = api_key or get_resend_api_key()

    if not key:
        raise ResendAuthError(
            "Missing Resend API key.\n"
            "Set RESEND_API_KEY environment variable or create credentials/resend/.env:\n"
            "  RESEND_API_KEY=re_xxx\n\n"
            "Get your API key at: https://resend.com/api-keys"
        )

    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def make_request(
    method: str,
    endpoint: str,
    api_key: Optional[str] = None,
    **kwargs,
) -> dict:
    """Make an authenticated request to Resend API.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint (e.g., '/emails/receiving')
        api_key: Override API key
        **kwargs: Additional arguments for requests

    Returns:
        JSON response as dict

    Raises:
        requests.HTTPError: On API errors
    """
    url = f"{RESEND_API_BASE}{endpoint}"
    headers = get_headers(api_key)

    response = requests.request(method, url, headers=headers, **kwargs)
    response.raise_for_status()

    return response.json() if response.content else {}
