"""DataForSEO On-Page endpoint: instant single-page technical SEO audit.

``on_page/instant_pages`` crawls one URL synchronously and returns its meta,
heading structure, and page-level SEO checks — the Technical pillar in one call.
"""

from typing import Any, Dict

from . import client


def instant_page(url: str, enable_javascript: bool = False) -> Dict[str, Any]:
    """Audit a single page's on-page SEO (title, meta, htags, checks).

    Endpoint: ``on_page/instant_pages``.
    """
    if not url:
        raise ValueError("No URL provided")

    task = client.post("on_page/instant_pages", [{
        "url": url,
        "enable_javascript": enable_javascript,
    }])
    result = client.first_result(task) or {}
    items = result.get("items") or []
    if not items:
        return {"success": False, "url": url, "cost": task.get("cost", 0),
                "error": "No page data returned (unreachable or blocked)"}

    page = items[0]
    meta = page.get("meta") or {}
    htags = meta.get("htags") or {}
    return {
        "success": True,
        "url": page.get("url", url),
        "cost": task.get("cost", 0),
        "status_code": page.get("status_code"),
        "title": meta.get("title"),
        "description": meta.get("description"),
        "canonical": meta.get("canonical"),
        "h1": htags.get("h1"),
        "internal_links_count": meta.get("internal_links_count"),
        "external_links_count": meta.get("external_links_count"),
        "images_count": meta.get("images_count"),
        "checks": page.get("checks"),
        "onpage_score": page.get("onpage_score"),
    }
