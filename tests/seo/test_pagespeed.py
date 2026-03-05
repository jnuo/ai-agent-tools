"""Tests for PageSpeed Insights module."""

from unittest.mock import patch, MagicMock

import pytest

from aitools.seo.pagespeed import run_pagespeed, _parse_pagespeed_response


SAMPLE_PAGESPEED_RESPONSE = {
    "id": "https://viziai.app/",
    "analysisUTCTimestamp": "2026-03-05T10:00:00.000Z",
    "loadingExperience": {
        "overall_category": "FAST",
        "metrics": {
            "LARGEST_CONTENTFUL_PAINT_MS": {
                "percentile": 1200,
                "category": "FAST",
                "distributions": [
                    {"proportion": 0.85},
                    {"proportion": 0.10},
                    {"proportion": 0.05},
                ],
            },
            "CUMULATIVE_LAYOUT_SHIFT_SCORE": {
                "percentile": 5,
                "category": "FAST",
                "distributions": [
                    {"proportion": 0.92},
                    {"proportion": 0.05},
                    {"proportion": 0.03},
                ],
            },
        },
    },
    "lighthouseResult": {
        "categories": {
            "performance": {"title": "Performance", "score": 0.91},
            "seo": {"title": "SEO", "score": 0.88},
        },
        "audits": {
            "largest-contentful-paint": {
                "title": "Largest Contentful Paint",
                "numericValue": 1200,
                "displayValue": "1.2 s",
                "score": 0.95,
            },
            "total-blocking-time": {
                "title": "Total Blocking Time",
                "numericValue": 100,
                "displayValue": "100 ms",
                "score": 0.92,
            },
            "cumulative-layout-shift": {
                "title": "Cumulative Layout Shift",
                "numericValue": 0.02,
                "displayValue": "0.02",
                "score": 0.99,
            },
            "first-contentful-paint": {
                "title": "First Contentful Paint",
                "numericValue": 700,
                "displayValue": "0.7 s",
                "score": 0.98,
            },
            "speed-index": {
                "title": "Speed Index",
                "numericValue": 1300,
                "displayValue": "1.3 s",
                "score": 0.92,
            },
            "interactive": {
                "title": "Time to Interactive",
                "numericValue": 1800,
                "displayValue": "1.8 s",
                "score": 0.90,
            },
            "render-blocking-resources": {
                "title": "Eliminate render-blocking resources",
                "score": 0.6,
                "displayValue": "Potential savings of 200 ms",
                "details": {
                    "type": "opportunity",
                    "overallSavingsMs": 200,
                    "overallSavingsBytes": 50000,
                },
            },
            "uses-text-compression": {
                "title": "Enable text compression",
                "score": 0.8,
                "displayValue": "Potential savings of 100 ms",
                "details": {
                    "type": "opportunity",
                    "overallSavingsMs": 100,
                    "overallSavingsBytes": 30000,
                },
            },
            "uses-optimized-images": {
                "title": "Efficiently encode images",
                "score": 1.0,
                "details": {"type": "opportunity", "overallSavingsMs": 0},
            },
        },
    },
}


class TestParsePagespeedResponse:
    """Tests for _parse_pagespeed_response."""

    def test_parses_scores(self):
        result = _parse_pagespeed_response(SAMPLE_PAGESPEED_RESPONSE)

        assert result["scores"]["performance"]["score"] == 91
        assert result["scores"]["seo"]["score"] == 88

    def test_parses_metrics(self):
        result = _parse_pagespeed_response(SAMPLE_PAGESPEED_RESPONSE)

        assert result["metrics"]["LCP"]["value"] == 1200
        assert result["metrics"]["TBT"]["value"] == 100
        assert result["metrics"]["CLS"]["value"] == 0.02
        assert result["metrics"]["FCP"]["value"] == 700
        assert result["metrics"]["SI"]["value"] == 1300
        assert result["metrics"]["TTI"]["value"] == 1800

    def test_parses_field_data(self):
        result = _parse_pagespeed_response(SAMPLE_PAGESPEED_RESPONSE)

        assert result["field_overall"] == "FAST"
        lcp = result["field_data"]["LARGEST_CONTENTFUL_PAINT_MS"]
        assert lcp["percentile"] == 1200
        assert lcp["category"] == "FAST"
        assert lcp["good"] == 0.85
        assert lcp["needs_improvement"] == 0.10
        assert lcp["poor"] == 0.05

    def test_parses_opportunities(self):
        result = _parse_pagespeed_response(SAMPLE_PAGESPEED_RESPONSE)

        opp_ids = [o["id"] for o in result["opportunities"]]
        assert "render-blocking-resources" in opp_ids
        assert "uses-text-compression" in opp_ids
        # score=1.0 should NOT appear as opportunity
        assert "uses-optimized-images" not in opp_ids

    def test_opportunities_sorted_by_savings(self):
        result = _parse_pagespeed_response(SAMPLE_PAGESPEED_RESPONSE)

        savings = [o["savings_ms"] for o in result["opportunities"]]
        assert savings == sorted(savings, reverse=True)

    def test_handles_no_field_data(self):
        data = {
            "id": "https://example.com",
            "loadingExperience": {},
            "lighthouseResult": {"categories": {}, "audits": {}},
        }
        result = _parse_pagespeed_response(data)

        assert result["field_data"] == {}
        assert result["field_overall"] == "N/A"

    def test_handles_empty_response(self):
        result = _parse_pagespeed_response({
            "loadingExperience": {},
            "lighthouseResult": {"categories": {}, "audits": {}},
        })

        assert result["scores"] == {}
        assert result["metrics"] == {}
        assert result["opportunities"] == []


class TestRunPagespeed:
    """Tests for run_pagespeed function."""

    @patch("aitools.seo.pagespeed.httpx")
    def test_calls_api_with_correct_params(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_PAGESPEED_RESPONSE
        mock_httpx.get.return_value = mock_response

        run_pagespeed("https://viziai.app", strategy="mobile", categories=["performance", "seo"])

        call_kwargs = mock_httpx.get.call_args
        assert call_kwargs[0][0] == "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        params = call_kwargs[1]["params"]
        # params is a list of tuples
        param_dict = {}
        param_categories = []
        for k, v in params:
            if k == "category":
                param_categories.append(v)
            else:
                param_dict[k] = v
        assert param_dict["url"] == "https://viziai.app"
        assert param_dict["strategy"] == "MOBILE"
        assert "PERFORMANCE" in param_categories
        assert "SEO" in param_categories

    @patch("aitools.seo.pagespeed.httpx")
    def test_desktop_strategy(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_PAGESPEED_RESPONSE
        mock_httpx.get.return_value = mock_response

        run_pagespeed("https://viziai.app", strategy="desktop")

        params = mock_httpx.get.call_args[1]["params"]
        param_dict = {k: v for k, v in params if k != "category"}
        assert param_dict["strategy"] == "DESKTOP"

    @patch("aitools.seo.pagespeed.httpx")
    def test_includes_api_key_when_provided(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_PAGESPEED_RESPONSE
        mock_httpx.get.return_value = mock_response

        run_pagespeed("https://viziai.app", api_key="test-key-123")

        params = mock_httpx.get.call_args[1]["params"]
        param_dict = {k: v for k, v in params if k != "category"}
        assert param_dict["key"] == "test-key-123"

    @patch("aitools.seo.pagespeed.httpx")
    def test_no_api_key_by_default(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_PAGESPEED_RESPONSE
        mock_httpx.get.return_value = mock_response

        run_pagespeed("https://viziai.app")

        params = mock_httpx.get.call_args[1]["params"]
        param_keys = [k for k, v in params]
        assert "key" not in param_keys

    @patch("aitools.seo.pagespeed.httpx")
    def test_raises_on_api_error(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_httpx.get.return_value = mock_response

        with pytest.raises(RuntimeError, match="PageSpeed API error.*429"):
            run_pagespeed("https://viziai.app")

    @patch("aitools.seo.pagespeed.httpx")
    def test_returns_parsed_result(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_PAGESPEED_RESPONSE
        mock_httpx.get.return_value = mock_response

        result = run_pagespeed("https://viziai.app")

        assert result["url"] == "https://viziai.app/"
        assert "performance" in result["scores"]
        assert "LCP" in result["metrics"]
        assert result["field_overall"] == "FAST"
