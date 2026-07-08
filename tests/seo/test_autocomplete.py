"""Tests for Google Autocomplete module."""

import json
from unittest.mock import patch, MagicMock

import pytest

from aitools.seo.autocomplete import get_autocomplete


def _mock_response(payload, status_code=200, *, content=None):
    """Build a mock httpx response.

    The module decodes ``response.content`` (raw bytes) itself rather than
    calling ``response.json()``, so tests must set ``.content`` to real bytes.
    Pass ``content`` directly to exercise non-UTF-8 / malformed payloads.
    """
    mock_response = MagicMock()
    mock_response.status_code = status_code
    if content is None:
        content = json.dumps(payload).encode("utf-8")
    mock_response.content = content
    return mock_response


class TestGetAutocomplete:
    """Tests for get_autocomplete function."""

    @patch("aitools.seo.autocomplete.httpx")
    def test_returns_suggestions(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response(
            [
                "kan tahlili",
                ["kan tahlili sonuçları", "kan tahlili ne demek", "kan tahlili aç karnına mı"],
            ]
        )

        result = get_autocomplete("kan tahlili")

        assert len(result) == 3
        assert "kan tahlili sonuçları" in result
        assert "kan tahlili ne demek" in result

    @patch("aitools.seo.autocomplete.httpx")
    def test_passes_correct_params(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response(["test", ["test result"]])

        get_autocomplete("test query", lang="tr", country="TR")

        call_kwargs = mock_httpx.get.call_args
        params = call_kwargs[1]["params"]
        assert params["q"] == "test query"
        assert params["hl"] == "tr"
        assert params["gl"] == "TR"
        assert params["client"] == "firefox"
        # UTF-8 is forced at the source so Google doesn't return latin-5.
        assert params["oe"] == "utf-8"
        assert params["ie"] == "utf-8"

    @patch("aitools.seo.autocomplete.httpx")
    def test_returns_empty_list_for_no_suggestions(self, mock_httpx):
        mock_httpx.get.return_value = _mock_response(["obscure query xyz"])

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
        mock_httpx.get.return_value = _mock_response(["q", []])

        get_autocomplete("q")

        params = mock_httpx.get.call_args[1]["params"]
        assert params["hl"] == "en"
        assert params["gl"] == "US"

    @patch("aitools.seo.autocomplete.httpx")
    def test_handles_stray_non_utf8_bytes(self, mock_httpx):
        """Regression: a legacy latin-5 (0xfd) byte must not crash decoding.

        Google occasionally returns ISO-8859-9 bytes for hl=tr. The previous
        ``response.json()`` path raised UnicodeDecodeError on byte 0xfd; the
        current path decodes with errors="replace" and keeps going.
        """
        # Valid UTF-8 JSON with a single stray latin-5 0xfd byte spliced in.
        content = b'["ajanda", ["ajanda uygulamas\xc4\xb1", "stray\xfdbyte"]]'
        mock_httpx.get.return_value = _mock_response(None, content=content)

        result = get_autocomplete("ajanda", lang="tr", country="TR")

        assert "ajanda uygulaması" in result
        # The stray byte is replaced (U+FFFD), not fatal.
        assert any("stray" in s for s in result)
