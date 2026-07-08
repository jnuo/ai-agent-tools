"""DataForSEO AI Optimization endpoints (GEO / AI-search visibility).

Two angles:
- :func:`ai_answer` — what an LLM actually replies to a prompt (does it mention
  your brand?), via ``ai_optimization/chat_gpt/llm_responses/live``.
- :func:`ai_search_volume` — how often a keyword is searched inside AI assistants,
  via ``ai_optimization/ai_keyword_data/keywords_search_volume/live``.
"""

from typing import Any, Dict, List

from . import client


def ai_answer(
    prompt: str,
    model_name: str = "gpt-4o-mini",
    max_output_tokens: int = 400,
    web_search: bool = False,
) -> Dict[str, Any]:
    """Get an LLM's answer to a prompt — the GEO 'do they mention us?' check.

    Endpoint: ``ai_optimization/chat_gpt/llm_responses/live``.
    """
    if not prompt:
        raise ValueError("No prompt provided")

    task = client.post("ai_optimization/chat_gpt/llm_responses/live", [{
        "user_prompt": prompt,
        "model_name": model_name,
        "max_output_tokens": max_output_tokens,
        "web_search": web_search,
    }])
    result = client.first_result(task) or {}

    texts: List[str] = []
    for item in result.get("items") or []:
        for section in item.get("sections") or []:
            if section.get("type") == "text" and section.get("text"):
                texts.append(section["text"])

    return {
        "success": True,
        "prompt": prompt,
        "model_name": result.get("model_name", model_name),
        "web_search": result.get("web_search"),
        "input_tokens": result.get("input_tokens"),
        "output_tokens": result.get("output_tokens"),
        "money_spent": result.get("money_spent"),
        "cost": task.get("cost", 0),
        "answer": "\n\n".join(texts),
    }


def ai_search_volume(
    keywords: List[str],
    country: str = "us",
    language: str = "en",
) -> Dict[str, Any]:
    """AI-assistant search volume per keyword (how often it's asked in AI chats).

    Endpoint: ``ai_optimization/ai_keyword_data/keywords_search_volume/live``.
    """
    if not keywords:
        raise ValueError("No keywords provided")

    location_code = client.resolve_location(country)
    lang_code = client.resolve_language(language)
    task = client.post("ai_optimization/ai_keyword_data/keywords_search_volume/live", [{
        "keywords": keywords,
        "location_code": location_code,
        "language_code": lang_code,
    }])
    result = client.first_result(task) or {}

    rows = [
        {"keyword": item.get("keyword"), "ai_search_volume": item.get("ai_search_volume")}
        for item in result.get("items") or []
    ]
    return {
        "success": True,
        "country": country,
        "language": language,
        "cost": task.get("cost", 0),
        "keywords": rows,
    }
