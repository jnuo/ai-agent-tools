"""Unit tests for aggregate.py — input validation."""

import pytest

from aitools.appsflyer.aggregate import (
    _validate_app_id,
    _validate_date_range,
)


def test_validate_app_id_accepts_ios_format():
    _validate_app_id("id6761076847")  # no raise


def test_validate_app_id_accepts_android_package():
    _validate_app_id("com.salta.dos")  # no raise


def test_validate_app_id_rejects_path_traversal():
    with pytest.raises(ValueError):
        _validate_app_id("../etc/passwd")


def test_validate_app_id_rejects_slash():
    with pytest.raises(ValueError):
        _validate_app_id("com.salta.dos/extra")


def test_validate_app_id_rejects_query_chars():
    with pytest.raises(ValueError):
        _validate_app_id("com.salta.dos?foo=bar")


def test_validate_app_id_rejects_empty():
    with pytest.raises(ValueError):
        _validate_app_id("")


def test_validate_date_range_accepts_equal():
    _validate_date_range("2026-05-15", "2026-05-15")  # no raise


def test_validate_date_range_accepts_forward():
    _validate_date_range("2026-05-09", "2026-05-15")  # no raise


def test_validate_date_range_rejects_inverted():
    with pytest.raises(ValueError, match="date_from"):
        _validate_date_range("2026-05-15", "2026-05-09")


def test_validate_date_range_rejects_bad_format():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        _validate_date_range("05/15/2026", "05/16/2026")
