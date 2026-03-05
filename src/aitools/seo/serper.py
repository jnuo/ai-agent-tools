"""Serper.dev Google SERP API client."""

import os
from pathlib import Path

import httpx


SERPER_API_BASE = "https://google.serper.dev"

# Endpoint mapping by search type
_ENDPOINTS = {
    "search": "/search",
    "news": "/news",
    "images": "/images",
}


class SerperAuthError(Exception):
    """Raised when Serper API key is missing."""
    pass


def _get_api_key() -> str:
    """Get Serper API key.

    Priority:
    1. SERPER_API_KEY environment variable
    2. ~/.config/aitools/serper_api_key file

    Returns:
        API key string

    Raises:
        SerperAuthError: If no API key found
    """
    # Check environment variable first
    api_key = os.environ.get("SERPER_API_KEY")
    if api_key:
        return api_key.strip()

    # Fall back to config file
    key_file = Path.home() / ".config" / "aitools" / "serper_api_key"
    if key_file.exists():
        content = key_file.read_text().strip()
        if content:
            return content

    raise SerperAuthError(
        "Missing Serper API key.\n"
        "Set SERPER_API_KEY environment variable, or save the key to:\n"
        "  ~/.config/aitools/serper_api_key\n\n"
        "Get your API key at: https://serper.dev/api-key"
    )


def search_serp(
    query: str,
    country: str = "us",
    lang: str = "en",
    num: int = 10,
    search_type: str = "search",
) -> dict:
    """Search Google via Serper.dev API.

    Args:
        query: Search query
        country: Country code (e.g., 'us', 'tr', 'es')
        lang: Language code (e.g., 'en', 'tr', 'es')
        num: Number of results (default 10)
        search_type: 'search', 'news', or 'images'

    Returns:
        Full Serper API response dict (contains organic, peopleAlsoAsk,
        relatedSearches, etc.)

    Raises:
        SerperAuthError: If no API key found
        ValueError: If search_type is invalid
        RuntimeError: If API request fails
    """
    if search_type not in _ENDPOINTS:
        raise ValueError(
            f"Invalid search_type '{search_type}'. "
            f"Must be one of: {', '.join(_ENDPOINTS.keys())}"
        )

    api_key = _get_api_key()
    endpoint = _ENDPOINTS[search_type]
    url = f"{SERPER_API_BASE}{endpoint}"

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "q": query,
        "gl": country,
        "hl": lang,
        "num": num,
    }

    response = httpx.post(url, headers=headers, json=payload, timeout=15.0)

    if response.status_code != 200:
        raise RuntimeError(
            f"Serper API error ({response.status_code}): {response.text}"
        )

    return response.json()
