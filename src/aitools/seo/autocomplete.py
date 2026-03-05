"""Google Autocomplete suggestions."""

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
    }

    response = httpx.get(url, params=params, timeout=10.0)

    if response.status_code != 200:
        raise RuntimeError(
            f"Google Autocomplete error ({response.status_code}): {response.text}"
        )

    data = response.json()

    # Response format: ["query", ["suggestion1", "suggestion2", ...]]
    return data[1] if len(data) > 1 else []
