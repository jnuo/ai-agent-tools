"""CLI tests for `aitools aso *` commands using Click's CliRunner."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from aitools.aso.cli import aso


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "aso_cli.db")


# ── add-app ────────────────────────────────────────────────────────────


def test_add_app_human_output(runner: CliRunner, db_path: str):
    result = runner.invoke(
        aso,
        ["add-app", "com.jnuo.salta", "salta", "--platform", "ios", "--db", db_path],
    )
    assert result.exit_code == 0
    assert "App registered" in result.output
    assert "com.jnuo.salta" in result.output


def test_add_app_json_output(runner: CliRunner, db_path: str):
    result = runner.invoke(
        aso,
        [
            "add-app",
            "com.jnuo.salta",
            "salta",
            "--platform",
            "android",
            "--country",
            "tr",
            "--db",
            db_path,
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output.strip())
    assert payload["bundle_id"] == "com.jnuo.salta"
    assert payload["platform"] == "android"
    assert payload["country"] == "tr"


def test_add_app_rejects_invalid_platform(runner: CliRunner, db_path: str):
    result = runner.invoke(
        aso,
        ["add-app", "com.jnuo.salta", "salta", "--platform", "windows", "--db", db_path],
    )
    assert result.exit_code != 0
    assert "Invalid value for '--platform'" in result.output


# ── apps (list) ────────────────────────────────────────────────────────


def test_apps_empty(runner: CliRunner, db_path: str):
    result = runner.invoke(aso, ["apps", "--db", db_path])
    assert result.exit_code == 0
    assert "No apps registered" in result.output


def test_apps_after_add(runner: CliRunner, db_path: str):
    runner.invoke(
        aso,
        ["add-app", "com.jnuo.salta", "salta", "--platform", "ios", "--db", db_path],
    )
    result = runner.invoke(aso, ["apps", "--db", db_path, "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert len(payload) == 1
    assert payload[0]["bundle_id"] == "com.jnuo.salta"


# ── import ─────────────────────────────────────────────────────────────


def test_import_search_terms(runner: CliRunner, tmp_path: Path, db_path: str):
    runner.invoke(
        aso,
        ["add-app", "com.jnuo.salta", "salta", "--platform", "ios", "--db", db_path],
    )
    data_file = tmp_path / "search_terms.json"
    data_file.write_text(
        json.dumps(
            [
                {"term": "daily planner", "impressions": 120, "taps": 20, "conversions": 5},
                {"term": "ai planner", "impressions": 80, "taps": 12, "conversions": 2},
            ]
        )
    )
    result = runner.invoke(
        aso,
        [
            "import",
            str(data_file),
            "--bundle-id",
            "com.jnuo.salta",
            "--platform",
            "ios",
            "--report-type",
            "search_terms",
            "--start",
            "2026-04-01",
            "--end",
            "2026-04-30",
            "--db",
            db_path,
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["rows_imported"] == 2


def test_import_search_terms_requires_end_date(
    runner: CliRunner, tmp_path: Path, db_path: str
):
    runner.invoke(
        aso,
        ["add-app", "com.jnuo.salta", "salta", "--platform", "ios", "--db", db_path],
    )
    data_file = tmp_path / "search_terms.json"
    data_file.write_text("[]")
    result = runner.invoke(
        aso,
        [
            "import",
            str(data_file),
            "--bundle-id",
            "com.jnuo.salta",
            "--platform",
            "ios",
            "--report-type",
            "search_terms",
            "--start",
            "2026-04-01",
            "--db",
            db_path,
        ],
    )
    assert result.exit_code != 0
    assert "--end is required" in result.output


def test_import_metadata_snapshot(
    runner: CliRunner, tmp_path: Path, db_path: str
):
    runner.invoke(
        aso,
        ["add-app", "com.jnuo.salta", "salta", "--platform", "ios", "--db", db_path],
    )
    data_file = tmp_path / "metadata.json"
    data_file.write_text(
        json.dumps(
            [
                {
                    "locale": "en-US",
                    "title": "Salta — Daily Planner",
                    "subtitle": "AI tasks, simply.",
                    "keywords_field": "planner,ai,tasks,goals",
                }
            ]
        )
    )
    result = runner.invoke(
        aso,
        [
            "import",
            str(data_file),
            "--bundle-id",
            "com.jnuo.salta",
            "--platform",
            "ios",
            "--report-type",
            "metadata",
            "--start",
            "2026-05-04",
            "--db",
            db_path,
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["locales_imported"] == 1


# ── trends ─────────────────────────────────────────────────────────────


def test_trends_no_data(runner: CliRunner, db_path: str):
    runner.invoke(
        aso,
        ["add-app", "com.jnuo.salta", "salta", "--platform", "ios", "--db", db_path],
    )
    result = runner.invoke(
        aso,
        [
            "trends",
            "--bundle-id",
            "com.jnuo.salta",
            "--platform",
            "ios",
            "--db",
            db_path,
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "error" in payload


# ── search ─────────────────────────────────────────────────────────────


def test_search_no_match(runner: CliRunner, db_path: str):
    result = runner.invoke(
        aso,
        ["search", "nonexistent", "--db", db_path],
    )
    assert result.exit_code == 0
    assert "No matches" in result.output


def test_search_requires_platform_with_bundle_id(
    runner: CliRunner, db_path: str
):
    result = runner.invoke(
        aso,
        [
            "search",
            "planner",
            "--bundle-id",
            "com.jnuo.salta",
            "--db",
            db_path,
        ],
    )
    assert result.exit_code != 0
    assert "--platform is required" in result.output


# ── stats ──────────────────────────────────────────────────────────────


def test_stats_empty(runner: CliRunner, db_path: str):
    result = runner.invoke(aso, ["stats", "--db", db_path])
    assert result.exit_code == 0
    assert "No apps registered" in result.output


def test_stats_after_import(runner: CliRunner, tmp_path: Path, db_path: str):
    runner.invoke(
        aso,
        ["add-app", "com.jnuo.salta", "salta", "--platform", "ios", "--db", db_path],
    )
    data_file = tmp_path / "search_terms.json"
    data_file.write_text(
        json.dumps([{"term": "planner", "impressions": 100}])
    )
    runner.invoke(
        aso,
        [
            "import",
            str(data_file),
            "--bundle-id",
            "com.jnuo.salta",
            "--platform",
            "ios",
            "--report-type",
            "search_terms",
            "--start",
            "2026-04-01",
            "--end",
            "2026-04-30",
            "--db",
            db_path,
        ],
    )
    result = runner.invoke(aso, ["stats", "--db", db_path, "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["total_snapshots"] == 1
    assert payload["apps"][0]["product"] == "salta"
