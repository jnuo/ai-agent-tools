"""DataForSEO Backlinks endpoints: domain authority summary + referring domains.

``rank`` (0-1000) is DataForSEO's domain-rank score — the closest available
proxy for Ahrefs DR / Moz DA.
"""

from typing import Any, Dict

from . import client


def summary(target: str) -> Dict[str, Any]:
    """Backlink profile summary for a domain: rank, backlinks, referring domains.

    Endpoint: ``backlinks/summary/live``.
    """
    task = client.post("backlinks/summary/live", [{
        "target": target,
        "backlinks_status_type": "live",
        "internal_list_limit": 10,
    }])
    result = client.first_result(task) or {}
    return {
        "success": True,
        "target": result.get("target", target),
        "cost": task.get("cost", 0),
        "rank": result.get("rank"),
        "backlinks": result.get("backlinks"),
        "referring_domains": result.get("referring_domains"),
        "referring_main_domains": result.get("referring_main_domains"),
        "referring_pages": result.get("referring_pages"),
        "backlinks_spam_score": result.get("backlinks_spam_score"),
        "broken_backlinks": result.get("broken_backlinks"),
        "first_seen": result.get("first_seen"),
        "referring_links_types": result.get("referring_links_types"),
    }


def referring_domains(target: str, limit: int = 50) -> Dict[str, Any]:
    """Top referring domains for a target, ordered by domain rank.

    Endpoint: ``backlinks/referring_domains/live``.
    """
    task = client.post("backlinks/referring_domains/live", [{
        "target": target,
        "backlinks_status_type": "live",
        "limit": limit,
        "order_by": ["rank,desc"],
    }])
    result = client.first_result(task) or {}
    domains = [
        {
            "domain": item.get("domain"),
            "rank": item.get("rank"),
            "backlinks": item.get("backlinks"),
            "spam_score": item.get("backlinks_spam_score"),
            "first_seen": item.get("first_seen"),
        }
        for item in result.get("items") or []
    ]
    return {
        "success": True,
        "target": result.get("target", target),
        "total_count": result.get("total_count"),
        "cost": task.get("cost", 0),
        "domains": domains,
    }
