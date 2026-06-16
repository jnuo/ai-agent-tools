"""Analytics Reports API flow: report request -> report -> instances -> segments.

High-level helpers return per-day aggregates for the two morning-block metrics:
- downloads        (report: "App Downloads Standard")
- product page views (report: "App Store Discovery and Engagement Standard")

Apple generates these reports asynchronously. A freshly created request has no
instances until Apple finishes processing (minutes to ~a day for the first
ONE_TIME_SNAPSHOT). Helpers raise ReportNotReady when no instances exist yet so
callers can surface a clear "still generating" message instead of empty data.
"""

from collections import defaultdict
from datetime import date, timedelta

from . import auth

DOWNLOADS_REPORT = "App Downloads Standard"
ENGAGEMENT_REPORT = "App Store Discovery and Engagement Standard"

# Verified against real report segments (2026-06).
_DATE_COLS = ("Date",)
_COUNT_COLS = ("Counts",)

# "Download Type" values that count as actual downloads (App Store "units").
# Updates/restores are NOT downloads.
_DOWNLOAD_TYPES = {"First-time download", "Redownload"}
_FIRST_TIME = "First-time download"

# The Engagement report's "Event" column mixes Impression / Page view / Tap.
# "Page view" events are store-listing page views (Page Type splits Product page
# vs Store sheet). Verified against real data (2026-06).
_PAGE_VIEW_EVENT = "Page view"
_IMPRESSION_EVENT = "Impression"

# An instance's processingDate runs ahead of the data dates it contains
# (Apple's reporting lag). Pull instances a few days past the requested window
# so late-arriving data for in-range dates is captured.
_LAG_BUFFER_DAYS = 5


class ReportNotReady(Exception):
    """Raised when a report exists but Apple has not produced instances yet."""


def _list_requests(app_id: str) -> list[dict]:
    return auth.paginate(
        f"/v1/apps/{app_id}/analyticsReportRequests", {"limit": 50}
    )


def ensure_request(app_id: str, access_type: str = "ONGOING") -> str:
    """Return an existing analyticsReportRequest id of the given access type,
    creating one if none exists. ONGOING refreshes daily; ONE_TIME_SNAPSHOT
    backfills history."""
    for req in _list_requests(app_id):
        attrs = req.get("attributes", {})
        if attrs.get("accessType") == access_type and not attrs.get("stoppedDueToInactivity"):
            return req["id"]
    body = {
        "data": {
            "type": "analyticsReportRequests",
            "attributes": {"accessType": access_type},
            "relationships": {"app": {"data": {"type": "apps", "id": app_id}}},
        }
    }
    return auth.api_post("/v1/analyticsReportRequests", body)["data"]["id"]


def _find_report_id(request_id: str, report_name: str) -> str | None:
    reports = auth.paginate(
        f"/v1/analyticsReportRequests/{request_id}/reports", {"limit": 200}
    )
    for r in reports:
        if r.get("attributes", {}).get("name") == report_name:
            return r["id"]
    return None


def _segment_rows(instance_id: str) -> list[dict]:
    segments = auth.paginate(
        f"/v1/analyticsReportInstances/{instance_id}/segments", {"limit": 200}
    )
    rows: list[dict] = []
    for seg in segments:
        url = seg.get("attributes", {}).get("url")
        if url:
            rows.extend(auth.download_report_segment(url))
    return rows


def _candidate_instances(app_id: str, report_name: str, date_from: str, date_to: str):
    """Yield (processingDate, access_type, instance_id) for instances that could
    contain data dates in [date_from, date_to].

    A daily instance's processingDate leads its data dates, so include instances
    up to date_to + buffer. ONE_TIME_SNAPSHOT instances hold history, so include
    all of them regardless of processingDate. Returns whether the report exists.
    """
    upper = (date.fromisoformat(date_to) + timedelta(days=_LAG_BUFFER_DAYS)).isoformat()
    found = False
    out = []
    for req in _list_requests(app_id):
        access = req.get("attributes", {}).get("accessType")
        report_id = _find_report_id(req["id"], report_name)
        if not report_id:
            continue
        found = True
        instances = auth.paginate(
            f"/v1/analyticsReports/{report_id}/instances",
            {"filter[granularity]": "DAILY", "limit": 200},
        )
        for inst in instances:
            pdate = inst.get("attributes", {}).get("processingDate", "")
            snapshot = access == "ONE_TIME_SNAPSHOT"
            if snapshot or (date_from <= pdate <= upper):
                out.append((pdate, access, inst["id"]))
    return found, out


def fetch_report_rows(app_id: str, report_name: str, date_from: str, date_to: str) -> list[dict]:
    """Segment rows whose data Date is in [date_from, date_to].

    Rows are filtered by their own "Date" column (not the instance processingDate).
    The same data date can appear in more than one instance (e.g. a ONGOING daily
    instance and the ONE_TIME_SNAPSHOT), so we de-duplicate by date: for each date
    we keep the single instance that carries the most rows for it (the most complete
    copy), breaking ties deterministically by processingDate then instance id. This
    avoids both double-counting and silently preferring a partial copy.

    Note: every candidate instance's segments are downloaded (no early exit), since
    a later instance may hold a more complete copy of an already-seen date. At
    weekly-window scale this is a handful of small gzipped files.

    Raises ReportNotReady if the report exists but no in-range data is available.
    """
    found, instances = _candidate_instances(app_id, report_name, date_from, date_to)
    if not found:
        raise ReportNotReady(
            f"Report '{report_name}' has not been generated for this app yet. "
            f"Run `setup` and wait for Apple to produce it."
        )

    # best[date] = (rank, rows) where rank = (row_count, processingDate, inst_id).
    best: dict[str, tuple[tuple, list[dict]]] = {}
    for pdate, _access, inst_id in instances:
        by_date: dict[str, list[dict]] = defaultdict(list)
        for r in _segment_rows(inst_id):
            d = r.get("Date", "")
            if date_from <= d <= date_to:
                by_date[d].append(r)
        for d, rs in by_date.items():
            rank = (len(rs), pdate, inst_id)
            if d not in best or rank > best[d][0]:
                best[d] = (rank, rs)

    rows = [r for _date, (_rank, rs) in best.items() for r in rs]
    if not rows:
        raise ReportNotReady(
            f"Report '{report_name}' exists but no data for {date_from}..{date_to} "
            f"is available yet (Apple's processing lag is ~1-2 days; the first "
            f"historical snapshot can take up to ~a day to generate)."
        )
    return rows


def _pick(colnames, candidates):
    for c in candidates:
        if c in colnames:
            return c
    return None


def daily_totals(rows: list[dict]) -> dict:
    """Sum the metric count column by Date. Returns {date: total}.

    Tolerant to Apple's exact count-column header (verified on first real data).
    """
    if not rows:
        return {}
    cols = rows[0].keys()
    date_col = _pick(cols, _DATE_COLS)
    count_col = _pick(cols, _COUNT_COLS)
    totals: dict[str, int] = defaultdict(int)
    for row in rows:
        d = row.get(date_col, "?") if date_col else "?"
        raw = (row.get(count_col, "0") if count_col else "0") or "0"
        try:
            totals[d] += int(float(str(raw).replace(",", "")))
        except ValueError:
            continue
    return dict(sorted(totals.items()))


def breakdown_by(rows: list[dict], dimension: str) -> dict:
    """Sum the count column grouped by an arbitrary dimension column."""
    if not rows or dimension not in rows[0]:
        return {}
    count_col = _pick(rows[0].keys(), _COUNT_COLS)
    out: dict[str, int] = defaultdict(int)
    for row in rows:
        raw = (row.get(count_col, "0") if count_col else "0") or "0"
        try:
            out[row.get(dimension, "?")] += int(float(str(raw).replace(",", "")))
        except ValueError:
            continue
    return dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))


def downloads(app_id: str, date_from: str, date_to: str) -> dict:
    """App downloads per day.

    'downloads' = First-time downloads + Redownloads (App Store "units").
    Updates/restores are excluded. First-time downloads (new installs) are also
    reported separately, plus the full Download Type breakdown for transparency.
    """
    rows = fetch_report_rows(app_id, DOWNLOADS_REPORT, date_from, date_to)
    download_rows = [r for r in rows if r.get("Download Type") in _DOWNLOAD_TYPES]
    first_time_rows = [r for r in rows if r.get("Download Type") == _FIRST_TIME]
    daily = daily_totals(download_rows)
    daily_ft = daily_totals(first_time_rows)
    return {
        "report": DOWNLOADS_REPORT,
        "range": {"from": date_from, "to": date_to},
        "daily": daily,
        "daily_first_time": daily_ft,
        "total": sum(daily.values()),
        "total_first_time": sum(daily_ft.values()),
        "by_download_type": breakdown_by(rows, "Download Type"),
        "by_territory": breakdown_by(download_rows, "Territory"),
        "columns": list(rows[0].keys()) if rows else [],
        "rows": rows,
    }


def page_views(app_id: str, date_from: str, date_to: str) -> dict:
    """Store-listing page views per day.

    The Engagement report's "Event" column mixes Impression / Page view / Tap;
    page views = Event == "Page view" only (summing all Counts would conflate
    impressions). Broken down by Page Type (Product page vs Store sheet). Total
    impressions are reported alongside for context.
    """
    rows = fetch_report_rows(app_id, ENGAGEMENT_REPORT, date_from, date_to)
    pv_rows = [r for r in rows if r.get("Event") == _PAGE_VIEW_EVENT]
    impression_rows = [r for r in rows if r.get("Event") == _IMPRESSION_EVENT]
    daily = daily_totals(pv_rows)
    return {
        "report": ENGAGEMENT_REPORT,
        "range": {"from": date_from, "to": date_to},
        "daily": daily,
        "total": sum(daily.values()),
        "total_impressions": sum(daily_totals(impression_rows).values()),
        "by_page_type": breakdown_by(pv_rows, "Page Type"),
        "by_source": breakdown_by(pv_rows, "Source Type"),
        "by_event": breakdown_by(rows, "Event"),
        "columns": list(rows[0].keys()) if rows else [],
        "rows": rows,
    }
