"""Tests for Google Autocomplete module."""

from unittest.mock import patch, MagicMock

import pytest

from aitools.seo.autocomplete import get_autocomplete


class TestGetAutocomplete:
    """Tests for get_autocomplete function."""

    @patch("aitools.seo.autocomplete.httpx")
    def test_returns_suggestions(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            "kan tahlili",
            ["kan tahlili sonuçları", "kan tahlili ne demek", "kan tahlili aç karnına mı"],
        ]
        mock_httpx.get.return_value = mock_response

        result = get_autocomplete("kan tahlili")

        assert len(result) == 3
        assert "kan tahlili sonuçları" in result
        assert "kan tahlili ne demek" in result

    @patch("aitools.seo.autocomplete.httpx")
    def test_passes_correct_params(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["test", ["test result"]]
        mock_httpx.get.return_value = mock_response

        get_autocomplete("test query", lang="tr", country="TR")

        call_kwargs = mock_httpx.get.call_args
        params = call_kwargs[1]["params"]
        assert params["q"] == "test query"
        assert params["hl"] == "tr"
        assert params["gl"] == "TR"
        assert params["client"] == "firefox"

    @patch("aitools.seo.autocomplete.httpx")
    def test_returns_empty_list_for_no_suggestions(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["obscure query xyz"]
        mock_httpx.get.return_value = mock_response

        result = get_autocomplete("obscure query xyz")

        assert result == []

    @patch("aitools.seo.autocomplete.httpx")
    def test_raises_on_http_error(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_httpx.get.return_value = mock_response

        with pytest.raises(RuntimeError, match="Google Autocomplete error.*403"):
            get_autocomplete("test")

    @patch("aitools.seo.autocomplete.httpx")
    def test_default_params(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["q", []]
        mock_httpx.get.return_value = mock_response

        get_autocomplete("q")

        params = mock_httpx.get.call_args[1]["params"]
        assert params["hl"] == "en"
        assert params["gl"] == "US"
