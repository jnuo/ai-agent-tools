"""AppsFlyer API authentication and HTTP helpers.

AppsFlyer Pull API V2 uses a single account-wide Bearer token.

IMPORTANT: All V2 tokens generated before 2026-03-10 19:00 UTC were revoked
by AppsFlyer. If your existing token stopped working in March 2026, regenerate
it in the dashboard at: Account → Security Center → API Tokens (V2).

Docs: https://dev.appsflyer.com/hc/reference/api-reference-overview
"""

import csv
import io
from typing import Optional

import requests

from ..config import get_appsflyer_api_token

# AppsFlyer Pull API base URL (all V2 endpoints live here)
APPSFLYER_API_BASE = "https://hq1.appsflyer.com"


class AppsFlyerAuthError(Exception):
    """Raised when AppsFlyer authentication fails or token is missing."""
    pass


class AppsFlyerAPIError(Exception):
    """Raised when an AppsFlyer API call fails with a non-auth error."""
    pass


def get_headers(api_token: Optional[str] = None) -> dict:
    """Get headers for AppsFlyer API requests.

    Args:
        api_token: Override token (uses config default if None)

    Returns:
        Headers dict including Bearer token

    Raises:
        AppsFlyerAuthError: If no token found
    """
    token = api_token or get_appsflyer_api_token()

    if not token:
        raise AppsFlyerAuthError(
            "Missing AppsFlyer API token.\n"
            "Set APPSFLYER_API_TOKEN environment variable, or create "
            "credentials/appsflyer/.env:\n"
            "  APPSFLYER_API_TOKEN=eyJhbG...\n\n"
            "Generate a V2 token in the dashboard: "
            "Account → Security Center → API Tokens (V2)\n"
            "Note: tokens created before 2026-03-10 19:00 UTC were revoked."
        )

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "text/csv",
    }


def make_csv_request(
    endpoint: str,
    params: Optional[dict] = None,
    api_token: Optional[str] = None,
    timeout: int = 60,
) -> list[dict]:
    """Make an authenticated GET request to AppsFlyer and parse CSV response.

    Pull API endpoints return CSV by default. This helper handles auth, the
    HTTP call, and CSV parsing into a list of dicts (first row = header).

    Args:
        endpoint: API path starting with '/' (e.g., '/api/agg-data/export/app/.../...')
        params: Query parameters dict
        api_token: Override token
        timeout: Request timeout in seconds (default 60 — AppsFlyer reports can be slow)

    Returns:
        List of dicts (one per CSV row), empty list if no data rows

    Raises:
        AppsFlyerAuthError: 401/403 response
        AppsFlyerAPIError: Other non-2xx responses
    """
    url = f"{APPSFLYER_API_BASE}{endpoint}"
    headers = get_headers(api_token)

    response = requests.get(url, headers=headers, params=params or {}, timeout=timeout)

    if response.status_code in (401, 403):
        raise AppsFlyerAuthError(
            f"AppsFlyer auth failed ({response.status_code}). "
            f"Token may be invalid, expired, or revoked. "
            f"Response: {response.text[:200]}"
        )
    if response.status_code == 404:
        raise AppsFlyerAPIError(
            f"AppsFlyer endpoint not found ({response.status_code}). "
            f"Check the app-id and report type. URL: {url}"
        )
    if not response.ok:
        raise AppsFlyerAPIError(
            f"AppsFlyer API error ({response.status_code}): {response.text[:500]}"
        )

    text = response.text.strip()
    if not text:
        return []

    reader = csv.DictReader(io.StringIO(text))
    return list(reader)
