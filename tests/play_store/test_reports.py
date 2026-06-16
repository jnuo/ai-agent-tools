"""Unit tests for play_store report helpers (pure logic, no network)."""

from aitools.play_store.reports import _months, _to_num


def test_months_single_month():
    assert _months("2026-06-13", "2026-06-14") == ["202606"]


def test_months_spans_two_months():
    assert _months("2026-05-28", "2026-06-03") == ["202605", "202606"]


def test_months_spans_year_boundary():
    assert _months("2025-12-20", "2026-02-05") == ["202512", "202601", "202602"]


def test_to_num_parses_and_defaults():
    assert _to_num("5") == 5.0
    assert _to_num("0.5") == 0.5
    assert _to_num("") == 0.0
    assert _to_num(None) == 0.0
    assert _to_num("n/a") == 0.0
