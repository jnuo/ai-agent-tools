"""Unit tests for pulse.py — composition + sorting + safety."""

import pytest

from aitools.appsflyer.pulse import (
    _safe_int,
    _top_partners_by_installs,
)


def test_safe_int_handles_numeric_string():
    assert _safe_int("42") == 42


def test_safe_int_handles_float_string():
    assert _safe_int("3.7") == 3


def test_safe_int_handles_na():
    """AppsFlyer returns 'N/A' liberally; must not crash."""
    assert _safe_int("N/A") == 0


def test_safe_int_handles_none():
    assert _safe_int(None) == 0


def test_safe_int_handles_empty_string():
    assert _safe_int("") == 0


def test_top_partners_empty_input():
    assert _top_partners_by_installs([]) == []


def test_top_partners_sorts_descending():
    rows = [
        {"Media Source": "A", "Installs": "3"},
        {"Media Source": "B", "Installs": "10"},
        {"Media Source": "C", "Installs": "5"},
    ]
    result = _top_partners_by_installs(rows, n=3)
    assert [r["Media Source"] for r in result] == ["B", "C", "A"]


def test_top_partners_n_zero_returns_empty():
    """Guards against silent-wrong slice behavior on n=0."""
    rows = [{"Media Source": "A", "Installs": "5"}]
    assert _top_partners_by_installs(rows, n=0) == []


def test_top_partners_n_negative_returns_empty():
    """Without the guard, n=-1 would return all-rows-minus-one (silently wrong)."""
    rows = [
        {"Media Source": "A", "Installs": "1"},
        {"Media Source": "B", "Installs": "2"},
    ]
    assert _top_partners_by_installs(rows, n=-1) == []


def test_top_partners_handles_missing_installs_column():
    """If AppsFlyer renames the column, rows treated as 0 installs (not crash)."""
    rows = [
        {"Media Source": "A"},
        {"Media Source": "B", "Installs": "5"},
    ]
    result = _top_partners_by_installs(rows, n=2)
    # B should be first (5 installs > A's missing-treated-as-0)
    assert result[0]["Media Source"] == "B"


def test_top_partners_limits_to_n():
    rows = [
        {"Media Source": f"M{i}", "Installs": str(i)} for i in range(10)
    ]
    result = _top_partners_by_installs(rows, n=3)
    assert len(result) == 3
