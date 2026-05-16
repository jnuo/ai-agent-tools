"""Unit tests for AppsFlyer auth helpers."""

import pytest

from aitools.appsflyer.auth import (
    AppsFlyerAuthError,
    AppsFlyerAPIError,
    AppsFlyerRateLimitError,
    get_headers,
    make_request,
)


def test_get_headers_raises_without_token(monkeypatch):
    monkeypatch.delenv("APPSFLYER_API_TOKEN", raising=False)
    # Point credentials dir somewhere with no .env so the file fallback misses too
    monkeypatch.setenv("AITOOLS_CREDENTIALS_DIR", "/tmp/aitools-test-nope")

    with pytest.raises(AppsFlyerAuthError):
        get_headers()


def test_get_headers_uses_env_token(monkeypatch):
    monkeypatch.setenv("APPSFLYER_API_TOKEN", "fake-token-abc")
    headers = get_headers()
    assert headers["Authorization"] == "Bearer fake-token-abc"
    assert headers["Accept"] == "text/csv"


def test_get_headers_explicit_override():
    headers = get_headers(api_key="explicit-token")
    assert headers["Authorization"] == "Bearer explicit-token"


def test_make_request_parses_csv(monkeypatch):
    """CSV parsing path — uses responses library to mock HTTP."""
    pytest.importorskip("responses")
    import responses

    monkeypatch.setenv("APPSFLYER_API_TOKEN", "fake-token")

    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://hq1.appsflyer.com/api/agg-data/export/app/com.example/daily_report/v5",
            body="Date,Installs\n2026-05-15,42\n2026-05-16,55\n",
            status=200,
            content_type="text/csv",
        )

        rows = make_request(
            "/api/agg-data/export/app/com.example/daily_report/v5",
            params={"from": "2026-05-15", "to": "2026-05-16"},
        )

    assert len(rows) == 2
    assert rows[0] == {"Date": "2026-05-15", "Installs": "42"}
    assert rows[1] == {"Date": "2026-05-16", "Installs": "55"}


def test_make_request_handles_401(monkeypatch):
    pytest.importorskip("responses")
    import responses

    monkeypatch.setenv("APPSFLYER_API_TOKEN", "bad-token")

    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://hq1.appsflyer.com/api/agg-data/export/app/com.example/daily_report/v5",
            body="unauthorized",
            status=401,
        )

        with pytest.raises(AppsFlyerAuthError):
            make_request(
                "/api/agg-data/export/app/com.example/daily_report/v5",
                params={"from": "2026-05-15", "to": "2026-05-15"},
            )


def test_make_request_distinguishes_403_rate_limit(monkeypatch):
    """AppsFlyer overloads 403 for both auth and rate-limit; we should split them."""
    pytest.importorskip("responses")
    import responses

    monkeypatch.setenv("APPSFLYER_API_TOKEN", "valid-token")

    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://hq1.appsflyer.com/api/agg-data/export/app/com.example/geo_report/v5",
            body="Limit reached for country-report",
            status=403,
        )

        with pytest.raises(AppsFlyerRateLimitError):
            make_request(
                "/api/agg-data/export/app/com.example/geo_report/v5",
                params={"from": "2026-05-09", "to": "2026-05-15"},
            )


def test_make_request_403_without_limit_is_auth_error(monkeypatch):
    """A 403 with no 'limit'/'quota' wording is treated as auth, not rate-limit."""
    pytest.importorskip("responses")
    import responses

    monkeypatch.setenv("APPSFLYER_API_TOKEN", "valid-but-scoped-out")

    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://hq1.appsflyer.com/api/agg-data/export/app/com.example/daily_report/v5",
            body="forbidden — app not in your account",
            status=403,
        )

        with pytest.raises(AppsFlyerAuthError):
            make_request(
                "/api/agg-data/export/app/com.example/daily_report/v5",
                params={"from": "2026-05-15", "to": "2026-05-15"},
            )


def test_make_request_403_empty_body_is_api_error_not_auth(monkeypatch):
    """A 403 with empty body is most likely a transient gateway — don't tell
    the user to regenerate their token."""
    pytest.importorskip("responses")
    import responses

    monkeypatch.setenv("APPSFLYER_API_TOKEN", "valid-token")

    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://hq1.appsflyer.com/api/agg-data/export/app/com.example/daily_report/v5",
            body="",
            status=403,
        )

        with pytest.raises(AppsFlyerAPIError) as exc_info:
            make_request(
                "/api/agg-data/export/app/com.example/daily_report/v5",
                params={"from": "2026-05-15", "to": "2026-05-15"},
            )

        # Must NOT be AppsFlyerAuthError (that prompts token regeneration)
        assert not isinstance(exc_info.value, AppsFlyerAuthError)
        # Must NOT be AppsFlyerRateLimitError either — empty body is ambiguous
        assert not isinstance(exc_info.value, AppsFlyerRateLimitError)


def test_sanitize_strips_ansi_from_error_bodies(monkeypatch):
    """Control characters in the response body must not leak into terminals."""
    pytest.importorskip("responses")
    import responses

    monkeypatch.setenv("APPSFLYER_API_TOKEN", "valid-token")

    # Body contains an ANSI escape sequence that would normally clear the
    # terminal and reposition the cursor.
    hostile_body = "\x1b[2J\x1b[H<INVISIBLE TAKEOVER>"

    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://hq1.appsflyer.com/api/agg-data/export/app/com.example/daily_report/v5",
            body=hostile_body,
            status=401,
        )

        with pytest.raises(AppsFlyerAuthError) as exc_info:
            make_request(
                "/api/agg-data/export/app/com.example/daily_report/v5",
                params={"from": "2026-05-15", "to": "2026-05-15"},
            )

        msg = str(exc_info.value)
        assert "\x1b" not in msg
        assert "<INVISIBLE TAKEOVER>" in msg
