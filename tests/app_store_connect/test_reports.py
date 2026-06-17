"""Unit tests for the tolerant report summarizers (pure logic, no network)."""

from aitools.app_store_connect.reports import daily_totals, breakdown_by, _pick


def test_pick_first_present_candidate():
    assert _pick({"Date", "Counts"}, ("Count", "Counts")) == "Counts"
    assert _pick({"Date"}, ("Counts", "Units")) is None


def test_daily_totals_sums_by_date():
    rows = [
        {"Date": "2026-06-13", "Counts": "2"},
        {"Date": "2026-06-13", "Counts": "3"},
        {"Date": "2026-06-14", "Counts": "5"},
    ]
    assert daily_totals(rows) == {"2026-06-13": 5, "2026-06-14": 5}


def test_daily_totals_handles_thousands_separators_and_blanks():
    rows = [
        {"Date": "2026-06-13", "Counts": "1,200"},
        {"Date": "2026-06-13", "Counts": ""},
        {"Date": "2026-06-13", "Counts": "not-a-number"},
    ]
    assert daily_totals(rows) == {"2026-06-13": 1200}


def test_daily_totals_empty():
    assert daily_totals([]) == {}


def test_daily_totals_falls_back_when_no_known_count_column():
    # Unknown count column -> 0s, but must not raise.
    rows = [{"Date": "2026-06-13", "Mystery": "9"}]
    assert daily_totals(rows) == {"2026-06-13": 0}


def test_breakdown_by_dimension_sorted_desc():
    rows = [
        {"Territory": "US", "Counts": "10"},
        {"Territory": "TR", "Counts": "25"},
        {"Territory": "US", "Counts": "5"},
    ]
    assert breakdown_by(rows, "Territory") == {"TR": 25, "US": 15}


def test_breakdown_by_missing_dimension_returns_empty():
    rows = [{"Date": "2026-06-13", "Counts": "10"}]
    assert breakdown_by(rows, "Territory") == {}
