"""Shared DataForSEO API client, location/language maps, and error handling.

All DataForSEO-backed SEO commands (Labs, Backlinks, AI Optimization, On-Page)
go through :func:`post` so auth, transport, and error surfacing stay identical.
"""

import base64
from typing import Any, Dict, List, Optional

import httpx

from .auth import require_credentials

API_BASE = "https://api.dataforseo.com/v3"

# DataForSEO location codes for common countries.
LOCATION_CODES: Dict[str, int] = {
    "us": 2840,      # United States
    "uk": 2826,      # United Kingdom
    "gb": 2826,      # United Kingdom (alias)
    "de": 2276,      # Germany
    "fr": 2250,      # France
    "es": 2724,      # Spain
    "it": 2380,      # Italy
    "nl": 2528,      # Netherlands
    "tr": 2792,      # Turkey
    "br": 2076,      # Brazil
    "mx": 2484,      # Mexico
    "ca": 2124,      # Canada
    "au": 2036,      # Australia
    "in": 2356,      # India
    "jp": 2392,      # Japan
}

# Language codes DataForSEO accepts as language_code.
LANGUAGE_CODES: Dict[str, str] = {
    "en": "en",
    "de": "de",
    "fr": "fr",
    "es": "es",
    "it": "it",
    "nl": "nl",
    "tr": "tr",
    "pt": "pt",
    "ja": "ja",
}


def resolve_location(country: str) -> int:
    """Map a country code (e.g. ``us``, ``tr``) to a DataForSEO location_code."""
    code = LOCATION_CODES.get(country.lower())
    if not code:
        raise ValueError(
            f"Unknown country code: {country}. "
            f"Supported: {', '.join(sorted(LOCATION_CODES))}"
        )
    return code


def resolve_language(language: str) -> str:
    """Map a language code to a DataForSEO language_code (pass-through fallback)."""
    return LANGUAGE_CODES.get(language.lower(), language.lower())


def _auth_header() -> str:
    login, password = require_credentials()
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    return f"Basic {token}"


def post(path: str, payload: List[Dict[str, Any]], timeout: float = 120.0) -> Dict[str, Any]:
    """POST a task array to a DataForSEO ``/live`` endpoint and return the first task.

    DataForSEO nests everything twice: a top-level envelope with an overall
    ``status_code``, then a ``tasks`` array (one per posted item) each with its
    own ``status_code``. This validates both layers and returns the first task
    dict (with ``result``, ``cost``, etc.), raising a clear ``ValueError`` on any
    failure — including funded-account edge cases like 40200 (payment required)
    and 40501 (invalid field).

    Args:
        path: Endpoint path after ``/v3/`` (e.g. ``dataforseo_labs/google/...``).
        payload: List of request objects (DataForSEO always wants an array).
        timeout: Request timeout in seconds.

    Returns:
        The first task dict from the response.

    Raises:
        ValueError: On network error, non-20000 envelope/task status, or empty tasks.
    """
    headers = {"Authorization": _auth_header(), "Content-Type": "application/json"}

    try:
        response = httpx.post(f"{API_BASE}/{path}", json=payload, headers=headers, timeout=timeout)
    except httpx.HTTPError as exc:
        raise ValueError(f"DataForSEO network error: {exc}") from exc

    if response.status_code != 200:
        raise ValueError(f"DataForSEO API error (HTTP {response.status_code}): {response.text}")

    result = response.json()

    if result.get("status_code") != 20000:
        raise ValueError(
            f"DataForSEO API error [{result.get('status_code')}]: "
            f"{result.get('status_message', 'Unknown error')}"
        )

    tasks = result.get("tasks") or []
    if not tasks:
        raise ValueError("DataForSEO returned no tasks")

    task = tasks[0]
    if task.get("status_code") != 20000:
        raise ValueError(
            f"DataForSEO task error [{task.get('status_code')}]: "
            f"{task.get('status_message', 'Task error')}"
        )

    return task


def first_result(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the first element of a task's ``result`` array, or ``None`` if empty."""
    result = task.get("result") or []
    return result[0] if result else None
