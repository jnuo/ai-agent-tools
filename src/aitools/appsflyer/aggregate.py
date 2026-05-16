"""AppsFlyer Aggregate Pull API V2 reports.

Aggregate endpoints have generous rate limits compared to raw data:
  - ≤ 2-day ranges: 1 call/min/app/report
  - ≥ 3-day ranges: 120 calls/day per account, 24 calls/day per app

Docs: https://support.appsflyer.com/hc/en-us/articles/207034346-Pull-API-aggregate-data
"""

import re
from datetime import date
from typing import Optional

from .auth import make_request

_AGG_BASE = "/api/agg-data/export/app"
_REPORT_VERSION = "v5"

# Real AppsFlyer app IDs are either "id<digits>" (iOS) or reverse-DNS package
# names (Android). Rejecting anything else prevents path-traversal in the URL
# (e.g., "../something/else") and surfaces typos early.
_APP_ID_RE = re.compile(r"^[\w.\-]+$")


def _validate_app_id(app_id: str) -> None:
    if not _APP_ID_RE.match(app_id):
        raise ValueError(
            f"Invalid app_id {app_id!r}. Expected iOS ID like 'id6761076847' "
            f"or Android package name like 'com.salta.dos'."
        )


def _validate_date_range(date_from: str, date_to: str) -> None:
    try:
        start = date.fromisoformat(date_from)
        end = date.fromisoformat(date_to)
    except ValueError as e:
        raise ValueError(f"Dates must be YYYY-MM-DD: {e}") from e
    if start > end:
        raise ValueError(
            f"date_from ({date_from}) must be <= date_to ({date_to})."
        )


def _report(
    app_id: str,
    report_type: str,
    date_from: str,
    date_to: str,
    media_source: Optional[str] = None,
    geo: Optional[str] = None,
    timezone: Optional[str] = None,
    currency: Optional[str] = None,
) -> list[dict]:
    """Internal helper for all aggregate report calls."""
    _validate_app_id(app_id)
    _validate_date_range(date_from, date_to)

    params: dict = {"from": date_from, "to": date_to}
    if media_source:
        params["media_source"] = media_source
    if geo:
        params["geo"] = geo
    if timezone:
        params["timezone"] = timezone
    if currency:
        params["currency"] = currency

    return make_request(
        f"{_AGG_BASE}/{app_id}/{report_type}/{_REPORT_VERSION}",
        params=params,
    )


def partners_report(app_id: str, date_from: str, date_to: str, **kwargs) -> list[dict]:
    """Partners report — aggregated by media source.

    Returns one row per partner with installs, loyal users, ROI, etc.
    """
    return _report(app_id, "partners_report", date_from, date_to, **kwargs)


def partners_by_date_report(app_id: str, date_from: str, date_to: str, **kwargs) -> list[dict]:
    """Partners by date — one row per (partner, date)."""
    return _report(app_id, "partners_by_date_report", date_from, date_to, **kwargs)


def daily_report(app_id: str, date_from: str, date_to: str, **kwargs) -> list[dict]:
    """Daily report — one row per date with aggregated install/event counts."""
    return _report(app_id, "daily_report", date_from, date_to, **kwargs)


def geo_report(app_id: str, date_from: str, date_to: str, **kwargs) -> list[dict]:
    """Geo report — one row per country with aggregated installs/events."""
    return _report(app_id, "geo_report", date_from, date_to, **kwargs)


def geo_by_date_report(app_id: str, date_from: str, date_to: str, **kwargs) -> list[dict]:
    """Geo by date — one row per (country, date)."""
    return _report(app_id, "geo_by_date_report", date_from, date_to, **kwargs)
