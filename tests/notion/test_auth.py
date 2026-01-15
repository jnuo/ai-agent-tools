"""Tests for Notion authentication module."""

import pytest
import responses
from requests import HTTPError

from aitools.notion.auth import (
    NOTION_API_BASE,
    NOTION_VERSION,
    NotionAuthError,
    get_headers,
    get_session,
    make_request,
    verify_connection,
)
from tests.conftest import get_request_body


class TestGetHeaders:
    """Tests for get_headers function."""

    def test_returns_headers_with_api_key(self, mock_notion_api_key):
        """Headers should include authorization, content-type, and version."""
        headers = get_headers()

        assert headers["Authorization"] == "Bearer secret_test_key_12345"
        assert headers["Content-Type"] == "application/json"
        assert headers["Notion-Version"] == NOTION_VERSION

    def test_uses_override_api_key(self, mock_notion_api_key):
        """Should use override API key when provided."""
        headers = get_headers(api_key="override_key")

        assert headers["Authorization"] == "Bearer override_key"

    def test_raises_error_without_api_key(self, monkeypatch, tmp_path):
        """Should raise NotionAuthError when no API key is available."""
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        # Point to empty temp dir to avoid loading from real .env file
        monkeypatch.setenv("AITOOLS_CREDENTIALS_DIR", str(tmp_path))

        with pytest.raises(NotionAuthError) as exc_info:
            get_headers()

        assert "Missing Notion API key" in str(exc_info.value)


class TestGetSession:
    """Tests for get_session function."""

    def test_returns_session_with_headers(self, mock_notion_api_key):
        """Session should have auth headers set."""
        session = get_session()

        assert "Authorization" in session.headers
        assert session.headers["Notion-Version"] == NOTION_VERSION


class TestMakeRequest:
    """Tests for make_request function."""

    @responses.activate
    def test_get_request(self, mock_notion_api_key):
        """Should make GET request and return JSON."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/pages/test-id",
            json={"id": "test-id", "object": "page"},
            status=200,
        )

        result = make_request("GET", "/pages/test-id")

        assert result["id"] == "test-id"
        assert len(responses.calls) == 1

    @responses.activate
    def test_post_request_with_json(self, mock_notion_api_key):
        """Should make POST request with JSON body."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/databases/db-id/query",
            json={"results": []},
            status=200,
        )

        result = make_request("POST", "/databases/db-id/query", json={"page_size": 10})

        assert result["results"] == []
        assert get_request_body(responses.calls[0]) == '{"page_size": 10}'

    @responses.activate
    def test_raises_http_error_on_failure(self, mock_notion_api_key):
        """Should raise HTTPError on non-2xx response."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/pages/bad-id",
            json={"code": "object_not_found"},
            status=404,
        )

        with pytest.raises(HTTPError):
            make_request("GET", "/pages/bad-id")

    @responses.activate
    def test_returns_empty_dict_for_empty_response(self, mock_notion_api_key):
        """Should return empty dict when response has no content."""
        responses.add(
            responses.DELETE,
            f"{NOTION_API_BASE}/blocks/block-id",
            body="",
            status=200,
        )

        result = make_request("DELETE", "/blocks/block-id")

        assert result == {}


class TestVerifyConnection:
    """Tests for verify_connection function."""

    @responses.activate
    def test_returns_bot_user_on_success(self, mock_notion_api_key, sample_user_response):
        """Should return bot user info on successful auth."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/users/me",
            json=sample_user_response,
            status=200,
        )

        result = verify_connection()

        assert result["id"] == "bot-user-id-12345"
        assert result["name"] == "Test Integration"

    @responses.activate
    def test_raises_auth_error_on_401(self, mock_notion_api_key):
        """Should raise NotionAuthError on 401 Unauthorized."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/users/me",
            json={"code": "unauthorized"},
            status=401,
        )

        with pytest.raises(NotionAuthError) as exc_info:
            verify_connection()

        assert "Invalid Notion API key" in str(exc_info.value)

    @responses.activate
    def test_reraises_other_http_errors(self, mock_notion_api_key):
        """Should re-raise non-401 HTTP errors."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/users/me",
            json={"code": "internal_server_error"},
            status=500,
        )

        with pytest.raises(HTTPError):
            verify_connection()
