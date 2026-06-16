"""Read Play install + store-performance reports into per-day aggregates.

Reports are monthly files of daily rows. A date range may span months, so we
load each YYYYMM file the range touches and filter rows by Date.
"""

from collections import defaultdict
from datetime import date

from . import auth

_INSTALLS_PREFIX = "stats/installs"
_STORE_PERF_PREFIX = "stats/store_performance"


def _months(date_from: str, date_to: str) -> list[str]:
    """List of YYYYMM strings covering [date_from, date_to] inclusive."""
    y, m = int(date_from[:4]), int(date_from[5:7])
    ey, em = int(date_to[:4]), int(date_to[5:7])
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y}{m:02d}")
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def _to_num(v):
    v = (v or "").strip()
    try:
        return float(v)
    except ValueError:
        return 0.0


def installs(package: str, date_from: str, date_to: str) -> dict:
    """Daily installs from the install overview reports.

    Returns daily 'Daily Device Installs' and 'Daily User Installs' within range.
    """
    daily_device: dict[str, int] = {}
    daily_user: dict[str, int] = {}
    active: dict[str, int] = {}
    for ym in _months(date_from, date_to):
        name = f"{_INSTALLS_PREFIX}/installs_{package}_{ym}_overview.csv"
        try:
            rows = auth.read_csv(name)
        except auth.PlayStoreAPIError:
            continue  # month file may not exist yet
        for r in rows:
            d = r.get("Date", "")
            if date_from <= d <= date_to:
                daily_device[d] = int(_to_num(r.get("Daily Device Installs")))
                daily_user[d] = int(_to_num(r.get("Daily User Installs")))
                active[d] = int(_to_num(r.get("Active Device Installs")))
    return {
        "package": package,
        "range": {"from": date_from, "to": date_to},
        "daily_device_installs": dict(sorted(daily_device.items())),
        "daily_user_installs": dict(sorted(daily_user.items())),
        "active_device_installs": dict(sorted(active.items())),
        "total_device_installs": sum(daily_device.values()),
        "total_user_installs": sum(daily_user.values()),
    }


def store_performance(package: str, date_from: str, date_to: str) -> dict:
    """Daily store-listing visitors + acquisitions, summed across countries.

    'Store listing visitors' is Play's equivalent of App Store product page views.
    """
    visitors: dict[str, int] = defaultdict(int)
    acquisitions: dict[str, int] = defaultdict(int)
    for ym in _months(date_from, date_to):
        name = f"{_STORE_PERF_PREFIX}/store_performance_{package}_{ym}_country.csv"
        try:
            rows = auth.read_csv(name)
        except auth.PlayStoreAPIError:
            continue
        for r in rows:
            d = r.get("Date", "")
            if date_from <= d <= date_to:
                visitors[d] += int(_to_num(r.get("Store listing visitors")))
                acquisitions[d] += int(_to_num(r.get("Store listing acquisitions")))
    total_v = sum(visitors.values())
    total_a = sum(acquisitions.values())
    return {
        "package": package,
        "range": {"from": date_from, "to": date_to},
        "daily_visitors": dict(sorted(visitors.items())),
        "daily_acquisitions": dict(sorted(acquisitions.items())),
        "total_visitors": total_v,
        "total_acquisitions": total_a,
        "conversion_rate": round(total_a / total_v, 4) if total_v else 0.0,
    }
