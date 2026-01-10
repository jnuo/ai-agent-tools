"""Notion API authentication."""

from typing import Optional

import requests

from ..config import get_notion_api_key

# Notion API base URL
NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionAuthError(Exception):
    """Raised when Notion authentication fails."""
    pass


def get_headers(api_key: Optional[str] = None) -> dict:
    """Get headers for Notion API requests.

    Args:
        api_key: Override API key (uses config default if None)

    Returns:
        Headers dict for requests

    Raises:
        NotionAuthError: If no API key found
    """
    key = api_key or get_notion_api_key()

    if not key:
        raise NotionAuthError(
            "Missing Notion API key.\n"
            "Set NOTION_API_KEY environment variable or create credentials/notion/.env:\n"
            "  NOTION_API_KEY=secret_xxx\n\n"
            "Get your API key at: https://www.notion.so/my-integrations"
        )

    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def get_session(api_key: Optional[str] = None) -> requests.Session:
    """Get a configured requests session for Notion API.

    Args:
        api_key: Override API key (uses config default if None)

    Returns:
        Configured requests.Session
    """
    session = requests.Session()
    session.headers.update(get_headers(api_key))
    return session


def make_request(
    method: str,
    endpoint: str,
    api_key: Optional[str] = None,
    **kwargs,
) -> dict:
    """Make an authenticated request to Notion API.

    Args:
        method: HTTP method (GET, POST, PATCH, DELETE)
        endpoint: API endpoint (e.g., '/pages/xxx')
        api_key: Override API key
        **kwargs: Additional arguments for requests

    Returns:
        JSON response as dict

    Raises:
        requests.HTTPError: On API errors
    """
    url = f"{NOTION_API_BASE}{endpoint}"
    headers = get_headers(api_key)

    response = requests.request(method, url, headers=headers, **kwargs)
    response.raise_for_status()

    return response.json() if response.content else {}


def verify_connection(api_key: Optional[str] = None) -> dict:
    """Verify API key works by fetching bot user info.

    Args:
        api_key: Override API key

    Returns:
        Bot user info dict

    Raises:
        NotionAuthError: If authentication fails
    """
    try:
        return make_request("GET", "/users/me", api_key=api_key)
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            raise NotionAuthError("Invalid Notion API key") from e
        raise
