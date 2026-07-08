"""Google Autocomplete suggestions."""

import json as _json

import httpx


def get_autocomplete(
    query: str,
    lang: str = "en",
    country: str = "US",
) -> list[str]:
    """Get Google Autocomplete suggestions for a query.

    Args:
        query: Search query to get suggestions for
        lang: Language code (e.g., 'en', 'tr', 'es')
        country: Country code (e.g., 'US', 'TR', 'ES')

    Returns:
        List of suggestion strings

    Raises:
        RuntimeError: If the request fails
    """
    url = "https://suggestqueries.google.com/complete/search"
    params = {
        "client": "firefox",
        "q": query,
        "hl": lang,
        "gl": country,
        # Force UTF-8 output. Without this, Google returns latin-5 (ISO-8859-9)
        # bytes for Turkish (hl=tr), which breaks response.json() with a
        # UnicodeDecodeError on byte 0xfd (ı/ş/ğ etc.).
        "oe": "utf-8",
        "ie": "utf-8",
    }

    response = httpx.get(url, params=params, timeout=10.0)

    if response.status_code != 200:
        raise RuntimeError(
            f"Google Autocomplete error ({response.status_code}): {response.text}"
        )

    # Decode from raw bytes with UTF-8 (oe=utf-8 above), replacing any stray
    # non-UTF-8 bytes rather than crashing. response.json() would re-detect the
    # encoding and choke on legacy latin-5 responses.
    data = _json.loads(response.content.decode("utf-8", "replace"))

    # Response format: ["query", ["suggestion1", "suggestion2", ...]]
    return data[1] if len(data) > 1 else []
