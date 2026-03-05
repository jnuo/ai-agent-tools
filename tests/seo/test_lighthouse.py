"""Tests for Lighthouse module."""

import json
from unittest.mock import patch

import pytest

from aitools.seo.lighthouse import run_lighthouse, _parse_lighthouse_output


# Sample Lighthouse JSON output (minimal but realistic)
SAMPLE_LIGHTHOUSE_OUTPUT = {
    "requestedUrl": "https://viziai.app",
    "fetchTime": "2026-03-05T10:00:00.000Z",
    "categories": {
        "performance": {"title": "Performance", "score": 0.92},
        "seo": {"title": "SEO", "score": 0.85},
        "accessibility": {"title": "Accessibility", "score": 0.78},
    },
    "audits": {
        "largest-contentful-paint": {
            "title": "Largest Contentful Paint",
            "numericValue": 1200.5,
            "displayValue": "1.2 s",
            "score": 0.95,
        },
        "total-blocking-time": {
            "title": "Total Blocking Time",
            "numericValue": 150,
            "displayValue": "150 ms",
            "score": 0.88,
        },
        "cumulative-layout-shift": {
            "title": "Cumulative Layout Shift",
            "numericValue": 0.05,
            "displayValue": "0.05",
            "score": 0.98,
        },
        "first-contentful-paint": {
            "title": "First Contentful Paint",
            "numericValue": 800,
            "displayValue": "0.8 s",
            "score": 0.97,
        },
        "speed-index": {
            "title": "Speed Index",
            "numericValue": 1500,
            "displayValue": "1.5 s",
            "score": 0.90,
        },
        "interactive": {
            "title": "Time to Interactive",
            "numericValue": 2000,
            "displayValue": "2.0 s",
            "score": 0.85,
        },
        "render-blocking-resources": {
            "title": "Eliminate render-blocking resources",
            "score": 0.5,
            "displayValue": "Potential savings of 300 ms",
        },
        "uses-optimized-images": {
            "title": "Efficiently encode images",
            "score": 1.0,
            "displayValue": "",
        },
    },
}


class TestParseLighthouseOutput:
    """Tests for _parse_lighthouse_output."""

    def test_parses_scores(self):
        result = _parse_lighthouse_output(SAMPLE_LIGHTHOUSE_OUTPUT)

        assert result["scores"]["performance"]["score"] == 92
        assert result["scores"]["performance"]["title"] == "Performance"
        assert result["scores"]["seo"]["score"] == 85
        assert result["scores"]["accessibility"]["score"] == 78

    def test_parses_metrics(self):
        result = _parse_lighthouse_output(SAMPLE_LIGHTHOUSE_OUTPUT)

        assert result["metrics"]["LCP"]["value"] == 1200.5
        assert result["metrics"]["LCP"]["display"] == "1.2 s"
        assert result["metrics"]["LCP"]["score"] == 95
        assert result["metrics"]["TBT"]["value"] == 150
        assert result["metrics"]["CLS"]["value"] == 0.05
        assert result["metrics"]["FCP"]["value"] == 800
        assert result["metrics"]["SI"]["value"] == 1500
        assert result["metrics"]["TTI"]["value"] == 2000

    def test_parses_url_and_fetch_time(self):
        result = _parse_lighthouse_output(SAMPLE_LIGHTHOUSE_OUTPUT)

        assert result["url"] == "https://viziai.app"
        assert result["fetch_time"] == "2026-03-05T10:00:00.000Z"

    def test_finds_failing_audits(self):
        result = _parse_lighthouse_output(SAMPLE_LIGHTHOUSE_OUTPUT)

        failing_ids = [a["id"] for a in result["failing_audits"]]
        assert "render-blocking-resources" in failing_ids
        # uses-optimized-images has score 1.0, should NOT be in failing
        assert "uses-optimized-images" not in failing_ids

    def test_failing_audits_sorted_by_score(self):
        result = _parse_lighthouse_output(SAMPLE_LIGHTHOUSE_OUTPUT)

        scores = [a["score"] for a in result["failing_audits"]]
        assert scores == sorted(scores)

    def test_handles_empty_data(self):
        result = _parse_lighthouse_output({})

        assert result["scores"] == {}
        assert result["metrics"] == {}
        assert result["failing_audits"] == []
        assert result["url"] == ""

    def test_handles_none_scores(self):
        """Categories with None scores should be treated as 0."""
        data = {
            "categories": {"performance": {"title": "Performance", "score": None}},
            "audits": {},
        }
        result = _parse_lighthouse_output(data)
        assert result["scores"]["performance"]["score"] == 0


class TestRunLighthouse:
    """Tests for run_lighthouse function."""

    @patch("aitools.seo.lighthouse.shutil.which")
    def test_raises_if_lighthouse_not_installed(self, mock_which):
        mock_which.return_value = None

        with pytest.raises(FileNotFoundError, match="npm install -g lighthouse"):
            run_lighthouse("https://example.com")

    @patch("aitools.seo.lighthouse.subprocess.run")
    @patch("aitools.seo.lighthouse.shutil.which")
    def test_runs_lighthouse_with_correct_args(self, mock_which, mock_run):
        mock_which.return_value = "/usr/local/bin/lighthouse"
        mock_run.return_value = type("Result", (), {
            "returncode": 0,
            "stdout": json.dumps(SAMPLE_LIGHTHOUSE_OUTPUT),
            "stderr": "",
        })()

        result = run_lighthouse("https://viziai.app", device="mobile")

        cmd = mock_run.call_args[0][0]
        assert "lighthouse" == cmd[0]
        assert "https://viziai.app" in cmd
        assert "--output=json" in cmd
        assert "--quiet" in cmd
        assert "--form-factor=mobile" in cmd

    @patch("aitools.seo.lighthouse.subprocess.run")
    @patch("aitools.seo.lighthouse.shutil.which")
    def test_desktop_adds_preset(self, mock_which, mock_run):
        mock_which.return_value = "/usr/local/bin/lighthouse"
        mock_run.return_value = type("Result", (), {
            "returncode": 0,
            "stdout": json.dumps(SAMPLE_LIGHTHOUSE_OUTPUT),
            "stderr": "",
        })()

        run_lighthouse("https://viziai.app", device="desktop")

        cmd = mock_run.call_args[0][0]
        assert "--preset=desktop" in cmd
        assert "--form-factor=desktop" in cmd

    @patch("aitools.seo.lighthouse.subprocess.run")
    @patch("aitools.seo.lighthouse.shutil.which")
    def test_passes_categories(self, mock_which, mock_run):
        mock_which.return_value = "/usr/local/bin/lighthouse"
        mock_run.return_value = type("Result", (), {
            "returncode": 0,
            "stdout": json.dumps(SAMPLE_LIGHTHOUSE_OUTPUT),
            "stderr": "",
        })()

        run_lighthouse("https://viziai.app", categories=["performance", "seo"])

        cmd = mock_run.call_args[0][0]
        assert "--only-categories=performance" in cmd
        assert "--only-categories=seo" in cmd

    @patch("aitools.seo.lighthouse.subprocess.run")
    @patch("aitools.seo.lighthouse.shutil.which")
    def test_raises_on_nonzero_exit(self, mock_which, mock_run):
        mock_which.return_value = "/usr/local/bin/lighthouse"
        mock_run.return_value = type("Result", (), {
            "returncode": 1,
            "stdout": "",
            "stderr": "Chrome connection failed",
        })()

        with pytest.raises(RuntimeError, match="Chrome connection failed"):
            run_lighthouse("https://viziai.app")

    @patch("aitools.seo.lighthouse.subprocess.run")
    @patch("aitools.seo.lighthouse.shutil.which")
    def test_returns_parsed_result(self, mock_which, mock_run):
        mock_which.return_value = "/usr/local/bin/lighthouse"
        mock_run.return_value = type("Result", (), {
            "returncode": 0,
            "stdout": json.dumps(SAMPLE_LIGHTHOUSE_OUTPUT),
            "stderr": "",
        })()

        result = run_lighthouse("https://viziai.app")

        assert result["url"] == "https://viziai.app"
        assert "performance" in result["scores"]
        assert "LCP" in result["metrics"]
