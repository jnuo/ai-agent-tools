"""Daily/weekly product pulse rollup for solo-dev usage."""

from datetime import date, timedelta
from typing import Optional

from . import aggregate


def _yesterday() -> str:
    return (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")


def _days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).strftime("%Y-%m-%d")


def daily_pulse(app_id: str, day: Optional[str] = None) -> dict:
    """Single-day rollup: total installs + top media sources.

    Args:
        app_id: AppsFlyer app ID (e.g., "id6761076847" for iOS, "com.salta.dos" for Android)
        day: ISO date string. Defaults to yesterday.

    Returns:
        Dict with `date`, `totals`, `top_partners` (top 5 by installs)
    """
    target = day or _yesterday()

    daily = aggregate.daily_report(app_id, target, target)
    partners = aggregate.partners_report(app_id, target, target)

    totals = daily[0] if daily else {}

    top_partners = sorted(
        partners,
        key=lambda r: int(_safe_int(r.get("Installs", 0))),
        reverse=True,
    )[:5]

    return {
        "app_id": app_id,
        "date": target,
        "totals": totals,
        "top_partners": top_partners,
    }


def weekly_pulse(app_id: str, end_day: Optional[str] = None) -> dict:
    """7-day rollup ending on `end_day` (defaults to yesterday).

    Returns dict with `range`, per-day breakdown, and partner totals over the window.
    """
    end = end_day or _yesterday()
    start = (date.fromisoformat(end) - timedelta(days=6)).strftime("%Y-%m-%d")

    daily = aggregate.daily_report(app_id, start, end)
    partners = aggregate.partners_report(app_id, start, end)

    top_partners = sorted(
        partners,
        key=lambda r: int(_safe_int(r.get("Installs", 0))),
        reverse=True,
    )[:5]

    return {
        "app_id": app_id,
        "range": {"from": start, "to": end},
        "daily": daily,
        "top_partners": top_partners,
    }


def _safe_int(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0
