"""PageSpeed Insights API v5 client."""

import httpx


def run_pagespeed(
    url: str,
    strategy: str = "mobile",
    categories: list[str] | None = None,
    api_key: str | None = None,
) -> dict:
    """Run PageSpeed Insights analysis on a URL.

    Args:
        url: URL to analyze
        strategy: 'mobile' or 'desktop'
        categories: List of categories (performance, seo, accessibility, best-practices)
        api_key: Optional Google API key for higher rate limits

    Returns:
        dict with 'scores', 'field_data' (CrUX), 'opportunities', and 'metrics'

    Raises:
        RuntimeError: If API request fails
    """

    if categories is None:
        categories = ["performance", "seo", "accessibility", "best-practices"]

    # Build params as list of tuples to support repeated 'category' key
    param_list = [
        ("url", url),
        ("strategy", "DESKTOP" if strategy == "desktop" else "MOBILE"),
    ]
    for cat in categories:
        # API uses UPPER_SNAKE category names
        cat_mapped = {
            "performance": "PERFORMANCE",
            "seo": "SEO",
            "accessibility": "ACCESSIBILITY",
            "best-practices": "BEST_PRACTICES",
        }.get(cat, cat.upper())
        param_list.append(("category", cat_mapped))

    if api_key:
        param_list.append(("key", api_key))

    api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

    response = httpx.get(api_url, params=param_list, timeout=60.0)

    if response.status_code != 200:
        raise RuntimeError(
            f"PageSpeed API error ({response.status_code}): {response.text}"
        )

    data = response.json()

    return _parse_pagespeed_response(data)


def _parse_pagespeed_response(data: dict) -> dict:
    """Parse PageSpeed Insights API response."""
    result = {
        "url": data.get("id", ""),
        "analysis_url": data.get("analysisUTCTimestamp", ""),
    }

    # Lighthouse scores
    lighthouse = data.get("lighthouseResult", {})
    scores = {}
    for cat_id, cat_data in lighthouse.get("categories", {}).items():
        scores[cat_id] = {
            "title": cat_data.get("title", cat_id),
            "score": round((cat_data.get("score") or 0) * 100),
        }
    result["scores"] = scores

    # Core Web Vitals from Lighthouse audits
    audits = lighthouse.get("audits", {})
    metrics = {}
    metric_keys = {
        "largest-contentful-paint": "LCP",
        "total-blocking-time": "TBT",
        "cumulative-layout-shift": "CLS",
        "first-contentful-paint": "FCP",
        "speed-index": "SI",
        "interactive": "TTI",
    }
    for audit_id, label in metric_keys.items():
        audit = audits.get(audit_id, {})
        if audit:
            metrics[label] = {
                "value": audit.get("numericValue"),
                "display": audit.get("displayValue", ""),
                "score": round((audit.get("score") or 0) * 100),
            }
    result["metrics"] = metrics

    # CrUX field data (if available)
    loading_exp = data.get("loadingExperience", {})
    field_data = {}
    crux_metrics = loading_exp.get("metrics", {})
    for metric_name, metric_data in crux_metrics.items():
        distributions = metric_data.get("distributions", [])
        field_data[metric_name] = {
            "percentile": metric_data.get("percentile"),
            "category": metric_data.get("category", ""),
            "good": distributions[0].get("proportion", 0) if len(distributions) > 0 else 0,
            "needs_improvement": distributions[1].get("proportion", 0) if len(distributions) > 1 else 0,
            "poor": distributions[2].get("proportion", 0) if len(distributions) > 2 else 0,
        }
    result["field_data"] = field_data
    result["field_overall"] = loading_exp.get("overall_category", "N/A")

    # Top opportunities (performance suggestions)
    opportunities = []
    for audit_id, audit in audits.items():
        details = audit.get("details", {})
        if details.get("type") == "opportunity" and audit.get("score") is not None and audit["score"] < 1:
            opportunities.append({
                "id": audit_id,
                "title": audit.get("title", ""),
                "savings_ms": details.get("overallSavingsMs", 0),
                "savings_bytes": details.get("overallSavingsBytes", 0),
                "display": audit.get("displayValue", ""),
            })

    # Sort by savings descending
    opportunities.sort(key=lambda o: o["savings_ms"], reverse=True)
    result["opportunities"] = opportunities

    result["raw"] = data

    return result
