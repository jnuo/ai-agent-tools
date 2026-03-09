"""Tests for Serper.dev module."""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from aitools.seo.serper import search_serp, _get_api_key, SerperAuthError


SAMPLE_SERP_RESPONSE = {
    "searchParameters": {"q": "kan tahlili takip", "gl": "tr", "hl": "tr"},
    "organic": [
        {
            "title": "Kan Tahlili Takip Uygulaması",
            "link": "https://viziai.app",
            "snippet": "AI-powered blood test tracking",
            "position": 1,
        },
        {
            "title": "e-Nabız Kan Sonuçları",
            "link": "https://enabiz.gov.tr",
            "snippet": "Devlet sağlık portalı",
            "position": 2,
        },
    ],
    "peopleAlsoAsk": [
        {"question": "Kan tahlili sonuçları ne zaman çıkar?"},
        {"question": "Kan tahlili aç karnına mı yapılır?"},
    ],
    "relatedSearches": [
        {"query": "kan tahlili değerleri"},
        {"query": "kan tahlili online"},
    ],
}


class TestGetApiKey:
    """Tests for _get_api_key function."""

    def test_reads_from_env_var(self, monkeypatch):
        monkeypatch.setenv("SERPER_API_KEY", "env-key-123")

        key = _get_api_key()
        assert key == "env-key-123"

    def test_strips_whitespace_from_env(self, monkeypatch):
        monkeypatch.setenv("SERPER_API_KEY", "  key-with-spaces  ")

        key = _get_api_key()
        assert key == "key-with-spaces"

    def test_reads_from_config_file(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SERPER_API_KEY", raising=False)

        config_dir = tmp_path / ".config" / "aitools"
        config_dir.mkdir(parents=True)
        key_file = config_dir / "serper_api_key"
        key_file.write_text("file-key-456\n")

        with patch.object(Path, "home", return_value=tmp_path):
            key = _get_api_key()
        assert key == "file-key-456"

    def test_env_var_takes_priority_over_file(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SERPER_API_KEY", "env-key")

        config_dir = tmp_path / ".config" / "aitools"
        config_dir.mkdir(parents=True)
        (config_dir / "serper_api_key").write_text("file-key")

        key = _get_api_key()
        assert key == "env-key"

    def test_raises_when_no_key(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SERPER_API_KEY", raising=False)

        with patch.object(Path, "home", return_value=tmp_path):
            with pytest.raises(SerperAuthError, match="Missing Serper API key"):
                _get_api_key()

    def test_raises_when_file_is_empty(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SERPER_API_KEY", raising=False)

        config_dir = tmp_path / ".config" / "aitools"
        config_dir.mkdir(parents=True)
        (config_dir / "serper_api_key").write_text("")

        with patch.object(Path, "home", return_value=tmp_path):
            with pytest.raises(SerperAuthError):
                _get_api_key()


class TestSearchSerp:
    """Tests for search_serp function."""

    @patch("aitools.seo.serper._get_api_key", return_value="test-key")
    @patch("aitools.seo.serper.httpx")
    def test_returns_serp_results(self, mock_httpx, mock_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_SERP_RESPONSE
        mock_httpx.post.return_value = mock_response

        result = search_serp("kan tahlili takip", country="tr", lang="tr")

        assert len(result["organic"]) == 2
        assert result["organic"][0]["title"] == "Kan Tahlili Takip Uygulaması"
        assert len(result["peopleAlsoAsk"]) == 2
        assert len(result["relatedSearches"]) == 2

    @patch("aitools.seo.serper._get_api_key", return_value="test-key")
    @patch("aitools.seo.serper.httpx")
    def test_sends_correct_request(self, mock_httpx, mock_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_SERP_RESPONSE
        mock_httpx.post.return_value = mock_response

        search_serp("test query", country="us", lang="en", num=5)

        call_args = mock_httpx.post.call_args
        assert call_args[0][0] == "https://google.serper.dev/search"
        assert call_args[1]["headers"]["X-API-KEY"] == "test-key"
        payload = call_args[1]["json"]
        assert payload["q"] == "test query"
        assert payload["gl"] == "us"
        assert payload["hl"] == "en"
        assert payload["num"] == 5

    @patch("aitools.seo.serper._get_api_key", return_value="test-key")
    @patch("aitools.seo.serper.httpx")
    def test_news_endpoint(self, mock_httpx, mock_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"news": []}
        mock_httpx.post.return_value = mock_response

        search_serp("test", search_type="news")

        url = mock_httpx.post.call_args[0][0]
        assert url == "https://google.serper.dev/news"

    @patch("aitools.seo.serper._get_api_key", return_value="test-key")
    @patch("aitools.seo.serper.httpx")
    def test_images_endpoint(self, mock_httpx, mock_key):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"images": []}
        mock_httpx.post.return_value = mock_response

        search_serp("test", search_type="images")

        url = mock_httpx.post.call_args[0][0]
        assert url == "https://google.serper.dev/images"

    def test_raises_on_invalid_search_type(self):
        with pytest.raises(ValueError, match="Invalid search_type"):
            search_serp("test", search_type="videos")

    @patch("aitools.seo.serper._get_api_key", return_value="test-key")
    @patch("aitools.seo.serper.httpx")
    def test_raises_on_api_error(self, mock_httpx, mock_key):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"
        mock_httpx.post.return_value = mock_response

        with pytest.raises(RuntimeError, match="Serper API error.*401"):
            search_serp("test")

    @patch("aitools.seo.serper._get_api_key", side_effect=SerperAuthError("Missing key"))
    def test_raises_when_no_api_key(self, mock_key):
        with pytest.raises(SerperAuthError, match="Missing key"):
            search_serp("test")
