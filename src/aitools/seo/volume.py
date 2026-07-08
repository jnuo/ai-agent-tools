"""Keyword search volume using the DataForSEO Google Ads API."""

from typing import Any, Dict, List

from . import client

# Re-exported for backwards compatibility (cli `countries`/`languages` commands
# and any callers importing these from volume). Source of truth is `client`.
LOCATION_CODES = client.LOCATION_CODES
LANGUAGE_CODES = client.LANGUAGE_CODES


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
    if not keywords:
        raise ValueError("No keywords provided")
    if len(keywords) > 1000:
        raise ValueError("Maximum 1000 keywords per request")

    location_code = client.resolve_location(country)
    lang_code = client.resolve_language(language)

    task = client.post("keywords_data/google_ads/search_volume/live", [{
        "keywords": keywords,
        "location_code": location_code,
        "language_code": lang_code,
        "include_serp_info": include_serp_info,
    }])

    keyword_results = []
    for item in task.get("result") or []:
        kw_data = {
            "keyword": item.get("keyword"),
            "search_volume": item.get("search_volume"),
            "competition": item.get("competition"),
            "competition_index": item.get("competition_index"),
            "cpc": item.get("cpc"),
            "low_top_of_page_bid": item.get("low_top_of_page_bid"),
            "high_top_of_page_bid": item.get("high_top_of_page_bid"),
        }
        monthly_searches = item.get("monthly_searches", [])
        if monthly_searches:
            kw_data["monthly_searches"] = monthly_searches
        if include_serp_info and item.get("serp_info"):
            kw_data["serp_info"] = item.get("serp_info")
        keyword_results.append(kw_data)

    return {
        "success": True,
        "country": country,
        "language": language,
        "location_code": location_code,
        "cost": task.get("cost", 0),
        "keywords": keyword_results,
    }
