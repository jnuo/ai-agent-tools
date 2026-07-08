"""DataForSEO Labs endpoints: ranked keywords, keyword difficulty, ideas,
suggestions, and search intent.

Labs endpoints require numeric ``location_code`` + ``language_code`` (the
Google-Ads-style ``location_name``/``language_name`` fields 400 here).
"""

from typing import Any, Dict, List

from . import client


def _kw_info(keyword_data: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten a Labs ``keyword_data`` block into a compact keyword row."""
    info = keyword_data.get("keyword_info") or {}
    props = keyword_data.get("keyword_properties") or {}
    return {
        "keyword": keyword_data.get("keyword"),
        "search_volume": info.get("search_volume"),
        "cpc": info.get("cpc"),
        "competition_level": info.get("competition_level"),
        "keyword_difficulty": props.get("keyword_difficulty"),
    }


def ranked_keywords(
    target: str,
    country: str = "us",
    language: str = "en",
    limit: int = 50,
) -> Dict[str, Any]:
    """Keywords a domain/URL already ranks for (competitor keyword research).

    Endpoint: ``dataforseo_labs/google/ranked_keywords/live``.
    """
    location_code = client.resolve_location(country)
    lang_code = client.resolve_language(language)
    task = client.post("dataforseo_labs/google/ranked_keywords/live", [{
        "target": target,
        "location_code": location_code,
        "language_code": lang_code,
        "limit": limit,
        "order_by": ["ranked_serp_element.serp_item.rank_group,asc"],
    }])
    result = client.first_result(task) or {}

    keywords: List[Dict[str, Any]] = []
    for item in result.get("items") or []:
        row = _kw_info(item.get("keyword_data") or {})
        serp_item = ((item.get("ranked_serp_element") or {}).get("serp_item") or {})
        row["rank_group"] = serp_item.get("rank_group")
        row["rank_absolute"] = serp_item.get("rank_absolute")
        row["url"] = serp_item.get("url")
        keywords.append(row)

    return {
        "success": True,
        "target": target,
        "country": country,
        "language": language,
        "total_count": result.get("total_count"),
        "cost": task.get("cost", 0),
        "keywords": keywords,
    }


def keyword_difficulty(
    keywords: List[str],
    country: str = "us",
    language: str = "en",
) -> Dict[str, Any]:
    """Real keyword difficulty (0-100) for up to 1000 keywords.

    Endpoint: ``dataforseo_labs/google/bulk_keyword_difficulty/live``.
    """
    if not keywords:
        raise ValueError("No keywords provided")
    if len(keywords) > 1000:
        raise ValueError("Maximum 1000 keywords per request")

    location_code = client.resolve_location(country)
    lang_code = client.resolve_language(language)
    task = client.post("dataforseo_labs/google/bulk_keyword_difficulty/live", [{
        "keywords": keywords,
        "location_code": location_code,
        "language_code": lang_code,
    }])
    result = client.first_result(task) or {}

    rows = [
        {"keyword": item.get("keyword"), "keyword_difficulty": item.get("keyword_difficulty")}
        for item in result.get("items") or []
    ]
    return {
        "success": True,
        "country": country,
        "language": language,
        "cost": task.get("cost", 0),
        "keywords": rows,
    }


def keyword_ideas(
    keywords: List[str],
    country: str = "us",
    language: str = "en",
    limit: int = 50,
) -> Dict[str, Any]:
    """Category-related keyword expansion with volume (broad ideas).

    Endpoint: ``dataforseo_labs/google/keyword_ideas/live``.
    """
    if not keywords:
        raise ValueError("No seed keywords provided")

    location_code = client.resolve_location(country)
    lang_code = client.resolve_language(language)
    task = client.post("dataforseo_labs/google/keyword_ideas/live", [{
        "keywords": keywords,
        "location_code": location_code,
        "language_code": lang_code,
        "limit": limit,
    }])
    return _parse_keyword_items(task, country, language)


def keyword_suggestions(
    seed: str,
    country: str = "us",
    language: str = "en",
    limit: int = 50,
) -> Dict[str, Any]:
    """Long-tail suggestions that contain the seed phrase, with volume.

    Endpoint: ``dataforseo_labs/google/keyword_suggestions/live``.
    """
    if not seed:
        raise ValueError("No seed keyword provided")

    location_code = client.resolve_location(country)
    lang_code = client.resolve_language(language)
    task = client.post("dataforseo_labs/google/keyword_suggestions/live", [{
        "keyword": seed,
        "location_code": location_code,
        "language_code": lang_code,
        "limit": limit,
    }])
    return _parse_keyword_items(task, country, language)


def search_intent(
    keywords: List[str],
    language: str = "en",
) -> Dict[str, Any]:
    """Classify keywords as informational/navigational/commercial/transactional.

    Endpoint: ``dataforseo_labs/google/search_intent/live`` (language only, no location).
    """
    if not keywords:
        raise ValueError("No keywords provided")

    lang_code = client.resolve_language(language)
    task = client.post("dataforseo_labs/google/search_intent/live", [{
        "keywords": keywords,
        "language_code": lang_code,
    }])
    result = client.first_result(task) or {}

    rows = []
    for item in result.get("items") or []:
        primary = item.get("keyword_intent") or {}
        secondary = item.get("secondary_keyword_intents") or []
        rows.append({
            "keyword": item.get("keyword"),
            "intent": primary.get("label"),
            "probability": primary.get("probability"),
            "secondary_intents": [
                {"label": s.get("label"), "probability": s.get("probability")}
                for s in secondary
            ],
        })
    return {
        "success": True,
        "language": language,
        "cost": task.get("cost", 0),
        "keywords": rows,
    }


def _parse_keyword_items(task: Dict[str, Any], country: str, language: str) -> Dict[str, Any]:
    """Shared parser for keyword_ideas / keyword_suggestions (same item shape)."""
    result = client.first_result(task) or {}
    keywords = []
    for item in result.get("items") or []:
        info = item.get("keyword_info") or {}
        keywords.append({
            "keyword": item.get("keyword"),
            "search_volume": info.get("search_volume"),
            "cpc": info.get("cpc"),
            "competition_level": info.get("competition_level"),
        })
    return {
        "success": True,
        "country": country,
        "language": language,
        "total_count": result.get("total_count"),
        "cost": task.get("cost", 0),
        "keywords": keywords,
    }
