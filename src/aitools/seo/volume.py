"""Keyword search volume using DataForSEO API."""

import base64
import json
from typing import Dict, List, Optional, Any
import urllib.request
import urllib.error

from .auth import require_credentials


# Location codes for common countries
LOCATION_CODES = {
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

# Language codes
LANGUAGE_CODES = {
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


def get_search_volume(
    keywords: List[str],
    country: str = "us",
    language: str = "en",
    include_serp_info: bool = False,
) -> Dict[str, Any]:
    """Get search volume for keywords using DataForSEO Google Ads API.

    Args:
        keywords: List of keywords (max 1000)
        country: Country code (us, uk, de, es, tr, etc.)
        language: Language code (en, de, es, tr, etc.)
        include_serp_info: Include SERP features info

    Returns:
        Dict with keyword data including search volume, CPC, competition

    Raises:
        ValueError: If credentials not configured or API error
    """
    login, password = require_credentials()

    # Validate inputs
    if not keywords:
        raise ValueError("No keywords provided")
    if len(keywords) > 1000:
        raise ValueError("Maximum 1000 keywords per request")

    # Get location code
    country_lower = country.lower()
    location_code = LOCATION_CODES.get(country_lower)
    if not location_code:
        raise ValueError(
            f"Unknown country code: {country}. "
            f"Supported: {', '.join(LOCATION_CODES.keys())}"
        )

    # Get language code
    lang_code = LANGUAGE_CODES.get(language.lower(), language.lower())

    # Prepare request
    url = "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"

    post_data = [{
        "keywords": keywords,
        "location_code": location_code,
        "language_code": lang_code,
        "include_serp_info": include_serp_info,
    }]

    # Create Basic Auth header
    credentials = f"{login}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json",
    }

    # Make request
    req = urllib.request.Request(
        url,
        data=json.dumps(post_data).encode(),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        raise ValueError(f"DataForSEO API error ({e.code}): {error_body}")
    except urllib.error.URLError as e:
        raise ValueError(f"Network error: {e.reason}")

    # Check for API errors
    if result.get("status_code") != 20000:
        error_msg = result.get("status_message", "Unknown error")
        raise ValueError(f"DataForSEO API error: {error_msg}")

    # Parse results
    tasks = result.get("tasks", [])
    if not tasks:
        return {"success": False, "error": "No results returned", "keywords": []}

    task = tasks[0]
    if task.get("status_code") != 20000:
        error_msg = task.get("status_message", "Task error")
        raise ValueError(f"DataForSEO task error: {error_msg}")

    # Extract keyword data
    keyword_results = []
    task_result = task.get("result", [])

    for item in task_result:
        kw_data = {
            "keyword": item.get("keyword"),
            "search_volume": item.get("search_volume"),
            "competition": item.get("competition"),
            "competition_index": item.get("competition_index"),
            "cpc": item.get("cpc"),
            "low_top_of_page_bid": item.get("low_top_of_page_bid"),
            "high_top_of_page_bid": item.get("high_top_of_page_bid"),
        }

        # Add monthly searches if available
        monthly_searches = item.get("monthly_searches", [])
        if monthly_searches:
            kw_data["monthly_searches"] = monthly_searches

        # Add SERP info if requested and available
        if include_serp_info and item.get("serp_info"):
            kw_data["serp_info"] = item.get("serp_info")

        keyword_results.append(kw_data)

    return {
        "success": True,
        "country": country,
        "language": language,
        "location_code": location_code,
        "cost": result.get("cost", 0),
        "keywords": keyword_results,
    }
