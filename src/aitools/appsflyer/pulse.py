"""Daily/weekly product pulse rollup for solo-dev usage.

Note on rate limits: each pulse call hits 2 aggregate reports (daily + partners).
The Aggregate Pull API enforces 1 call/min/report for short ranges, so calling
`daily_pulse` twice in <60s for the same app will hit a rate-limit error on
the second call.
"""

from datetime import date, timedelta
from typing import Optional

from . import aggregate

# AppsFlyer CSV column names. Centralized here because the same headers are
# referenced across pulse + cli, and AppsFlyer occasionally renames them.
_INSTALLS_COL = "Installs"


def _yesterday() -> str:
    return (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")


def _safe_int(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _top_partners_by_installs(rows: list[dict], n: int = 5) -> list[dict]:
    return sorted(
        rows,
        key=lambda r: _safe_int(r.get(_INSTALLS_COL, 0)),
        reverse=True,
    )[:n]


def daily_pulse(app_id: str, day: Optional[str] = None) -> dict:
    """Single-day rollup: total installs + top media sources.

    Args:
        app_id: AppsFlyer app ID (e.g., "id6761076847" for iOS, "com.salta.dos" for Android)
        day: ISO date string. Defaults to yesterday.

    Returns:
        Dict with `date`, `totals`, `top_partners` (top 5 by installs)
    """
    target = day or _yesterday()

    daily_rows = aggregate.daily_report(app_id, target, target)
    partners = aggregate.partners_report(app_id, target, target)

    totals = daily_rows[0] if daily_rows else {}

    return {
        "app_id": app_id,
        "date": target,
        "totals": totals,
        "top_partners": _top_partners_by_installs(partners),
    }


def weekly_pulse(app_id: str, end_day: Optional[str] = None) -> dict:
    """7-day rollup ending on `end_day` (defaults to yesterday).

    Returns dict with `range`, per-day breakdown, and partner totals over the window.
    """
    end = end_day or _yesterday()
    start = (date.fromisoformat(end) - timedelta(days=6)).strftime("%Y-%m-%d")

    daily_rows = aggregate.daily_report(app_id, start, end)
    partners = aggregate.partners_report(app_id, start, end)

    return {
        "app_id": app_id,
        "range": {"from": start, "to": end},
        "daily": daily_rows,
        "top_partners": _top_partners_by_installs(partners),
    }
