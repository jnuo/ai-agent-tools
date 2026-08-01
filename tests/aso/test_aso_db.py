"""Unit tests for AsoDb — schema, app registration, snapshot lifecycle, trends, FTS."""

from pathlib import Path

import pytest

from aitools.aso.aso import AsoDb


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def db(tmp_path: Path) -> AsoDb:
    """A fresh AsoDb on a temp file. Closes after each test."""
    db_path = tmp_path / "aso_test.db"
    aso = AsoDb(db_path)
    yield aso
    aso.close()


@pytest.fixture
def salta_ios(db: AsoDb) -> int:
    """Pre-registered Salta iOS app."""
    return db.add_app("com.jnuo.salta", "salta", "ios")


@pytest.fixture
def salta_android(db: AsoDb) -> int:
    """Pre-registered Salta Android app."""
    return db.add_app("com.jnuo.salta", "salta", "android")


# ── App registration ────────────────────────────────────────────────────


class TestAddApp:
    def test_returns_new_id(self, db: AsoDb):
        app_id = db.add_app("com.jnuo.salta", "salta", "ios")
        assert app_id == 1

    def test_idempotent_on_same_triple(self, db: AsoDb):
        first = db.add_app("com.jnuo.salta", "salta", "ios")
        second = db.add_app("com.jnuo.salta", "salta", "ios")
        assert first == second

    def test_same_bundle_different_platform_creates_two_rows(self, db: AsoDb):
        ios = db.add_app("com.jnuo.salta", "salta", "ios")
        android = db.add_app("com.jnuo.salta", "salta", "android")
        assert ios != android
        assert len(db.list_apps()) == 2

    def test_same_bundle_different_country_creates_two_rows(self, db: AsoDb):
        us = db.add_app("com.jnuo.salta", "salta", "ios", "us")
        tr = db.add_app("com.jnuo.salta", "salta", "ios", "tr")
        assert us != tr
        assert len(db.list_apps()) == 2

    def test_country_lowercased(self, db: AsoDb):
        upper = db.add_app("com.jnuo.salta", "salta", "ios", "US")
        lower = db.add_app("com.jnuo.salta", "salta", "ios", "us")
        assert upper == lower, "Country should be normalized to lowercase"

    def test_invalid_platform_raises(self, db: AsoDb):
        with pytest.raises(ValueError, match="platform must be one of"):
            db.add_app("com.jnuo.salta", "salta", "windows")

    def test_get_app_returns_none_for_missing(self, db: AsoDb):
        assert db.get_app("not.an.app", "ios") is None

    def test_get_app_returns_dict(self, db: AsoDb, salta_ios: int):
        app = db.get_app("com.jnuo.salta", "ios")
        assert app is not None
        assert app["id"] == salta_ios
        assert app["product"] == "salta"
        assert app["platform"] == "ios"


# ── Search-term import + re-import ──────────────────────────────────────


class TestImportSearchTerms:
    def test_imports_basic_rows(self, db: AsoDb, salta_ios: int):
        rows = [
            {"term": "daily planner", "impressions": 100, "taps": 20, "conversions": 5},
            {"term": "ai planner", "impressions": 50, "taps": 8, "conversions": 2},
        ]
        result = db.import_search_terms(
            "com.jnuo.salta", "ios", "2026-04-01", "2026-04-30", rows
        )
        assert result["rows_imported"] == 2
        assert result["report_type"] == "search_terms"

    def test_raises_for_unregistered_app(self, db: AsoDb):
        with pytest.raises(ValueError, match="not registered"):
            db.import_search_terms(
                "not.an.app", "ios", "2026-04-01", "2026-04-30", []
            )

    def test_handles_empty_rows(self, db: AsoDb, salta_ios: int):
        result = db.import_search_terms(
            "com.jnuo.salta", "ios", "2026-04-01", "2026-04-30", []
        )
        assert result["rows_imported"] == 0

    def test_reimport_overwrites_old_data(self, db: AsoDb, salta_ios: int):
        first = [{"term": "old term", "impressions": 100}]
        second = [{"term": "new term", "impressions": 200}]
        db.import_search_terms(
            "com.jnuo.salta", "ios", "2026-04-01", "2026-04-30", first
        )
        db.import_search_terms(
            "com.jnuo.salta", "ios", "2026-04-01", "2026-04-30", second
        )
        # Same period imported twice — only new data should remain.
        results = db.search_terms_fts("term", "com.jnuo.salta", "ios")
        terms = {r["term"] for r in results}
        assert "old term" not in terms
        assert "new term" in terms

    def test_default_values_for_missing_fields(self, db: AsoDb, salta_ios: int):
        rows = [{"term": "minimal"}]  # only term, no metrics
        db.import_search_terms(
            "com.jnuo.salta", "ios", "2026-04-01", "2026-04-30", rows
        )
        results = db.search_terms_fts("minimal", "com.jnuo.salta", "ios")
        assert len(results) == 1
        assert results[0]["impressions"] == 0
        assert results[0]["taps"] == 0
        assert results[0]["conversions"] == 0


# ── Metadata / reviews / rankings imports ───────────────────────────────


class TestImportMetadata:
    def test_imports_locales(self, db: AsoDb, salta_ios: int):
        locales = [
            {
                "locale": "en-US",
                "title": "Salta — Daily Planner",
                "subtitle": "AI tasks, simply.",
                "keywords_field": "planner,ai,tasks,goals",
            },
            {
                "locale": "tr-TR",
                "title": "Salta — Günlük Planlayıcı",
            },
        ]
        result = db.import_metadata(
            "com.jnuo.salta", "ios", "2026-05-04", locales
        )
        assert result["locales_imported"] == 2

    def test_reimport_overwrites_metadata(self, db: AsoDb, salta_ios: int):
        first = [{"locale": "en-US", "title": "Old Title"}]
        second = [{"locale": "en-US", "title": "New Title"}]
        db.import_metadata("com.jnuo.salta", "ios", "2026-05-04", first)
        db.import_metadata("com.jnuo.salta", "ios", "2026-05-04", second)

        rows = db.conn.execute(
            "SELECT title FROM metadata_snapshots ORDER BY id"
        ).fetchall()
        # After re-import, only the new row should remain
        assert len(rows) == 1
        assert rows[0]["title"] == "New Title"


class TestImportReviews:
    def test_imports_reviews(self, db: AsoDb, salta_ios: int):
        reviews = [
            {
                "review_id": "r1",
                "rating": 5,
                "title": "Great",
                "body": "Love this app for planning my day",
                "version": "1.14.2",
                "country": "US",
                "locale": "en-US",
                "posted_at": "2026-04-15T10:00:00Z",
            },
            {
                "review_id": "r2",
                "rating": 2,
                "title": "Crashes",
                "body": "Crashes on Xiaomi when keyboard opens",
                "version": "1.14.1",
                "country": "TR",
                "locale": "tr-TR",
                "posted_at": "2026-04-20T08:00:00Z",
            },
        ]
        result = db.import_reviews(
            "com.jnuo.salta", "ios", "2026-04-01", "2026-04-30", reviews
        )
        assert result["rows_imported"] == 2

    def test_handles_missing_rating(self, db: AsoDb, salta_ios: int):
        reviews = [{"review_id": "r1", "title": "no rating"}]
        result = db.import_reviews(
            "com.jnuo.salta", "ios", "2026-04-01", "2026-04-30", reviews
        )
        assert result["rows_imported"] == 1


class TestImportRankings:
    def test_imports_rankings(self, db: AsoDb, salta_ios: int):
        rows = [
            {"keyword": "daily planner", "rank": 47},
            {"keyword": "ai planner", "rank": 12},
            {"keyword": "task manager", "rank": None},  # not ranking
        ]
        result = db.import_rankings(
            "com.jnuo.salta", "ios", "2026-05-04", rows
        )
        assert result["rows_imported"] == 3


# ── Trends: search terms ────────────────────────────────────────────────


class TestSearchTermTrends:
    def test_no_snapshots_returns_error(self, db: AsoDb, salta_ios: int):
        result = db.compute_search_term_trends("com.jnuo.salta", "ios")
        assert "error" in result

    def test_single_snapshot_returns_top_terms(self, db: AsoDb, salta_ios: int):
        rows = [
            {"term": "alpha", "impressions": 300},
            {"term": "beta", "impressions": 200},
            {"term": "gamma", "impressions": 100},
        ]
        db.import_search_terms(
            "com.jnuo.salta", "ios", "2026-04-01", "2026-04-30", rows
        )
        result = db.compute_search_term_trends("com.jnuo.salta", "ios")
        assert result["mode"] == "single_snapshot"
        assert len(result["top_terms"]) == 3
        # Sorted by impressions DESC
        assert result["top_terms"][0]["term"] == "alpha"

    def test_two_snapshots_classify_correctly(self, db: AsoDb, salta_ios: int):
        previous = [
            {"term": "stable", "impressions": 100},
            {"term": "declining", "impressions": 200},
            {"term": "lost", "impressions": 50},
        ]
        current = [
            {"term": "stable", "impressions": 105},  # within ±20% — neither rising nor declining
            {"term": "rising", "impressions": 300},  # new + rising
            {"term": "declining", "impressions": 100},  # impressions halved
            # "lost" is in previous but not current
        ]
        db.import_search_terms(
            "com.jnuo.salta", "ios", "2026-03-01", "2026-03-31", previous
        )
        db.import_search_terms(
            "com.jnuo.salta", "ios", "2026-04-01", "2026-04-30", current
        )

        result = db.compute_search_term_trends("com.jnuo.salta", "ios")
        assert result["mode"] == "comparison"

        rising_terms = {r["term"] for r in result["rising"]}
        declining_terms = {r["term"] for r in result["declining"]}
        new_terms = {r["term"] for r in result["new"]}
        lost_terms = {r["term"] for r in result["lost"]}

        assert "rising" in new_terms  # appeared in current only
        assert "declining" in declining_terms
        assert "lost" in lost_terms
        # "stable" should not appear in any movement bucket
        assert "stable" not in rising_terms
        assert "stable" not in declining_terms

    def test_app_must_exist(self, db: AsoDb):
        with pytest.raises(ValueError, match="App not found"):
            db.compute_search_term_trends("not.an.app", "ios")


# ── Trends: rankings ────────────────────────────────────────────────────


class TestRankingTrends:
    def test_needs_two_snapshots(self, db: AsoDb, salta_ios: int):
        db.import_rankings(
            "com.jnuo.salta", "ios", "2026-05-01", [{"keyword": "kw", "rank": 50}]
        )
        result = db.compute_ranking_trends("com.jnuo.salta", "ios")
        assert "error" in result
        assert result["snapshots_available"] == 1

    def test_lower_rank_is_rising(self, db: AsoDb, salta_ios: int):
        # Day 1: rank 50, Day 2: rank 30 → improving (rising).
        db.import_rankings(
            "com.jnuo.salta", "ios", "2026-05-01", [{"keyword": "planner", "rank": 50}]
        )
        db.import_rankings(
            "com.jnuo.salta", "ios", "2026-05-04", [{"keyword": "planner", "rank": 30}]
        )
        result = db.compute_ranking_trends("com.jnuo.salta", "ios")
        rising_keywords = {r["keyword"] for r in result["rising"]}
        assert "planner" in rising_keywords
        assert result["counts"]["rising"] == 1
        assert result["counts"]["declining"] == 0


# ── FTS search ──────────────────────────────────────────────────────────


class TestSearchTermsFts:
    def test_finds_matching_term(self, db: AsoDb, salta_ios: int):
        db.import_search_terms(
            "com.jnuo.salta",
            "ios",
            "2026-04-01",
            "2026-04-30",
            [{"term": "daily planner", "impressions": 100}],
        )
        results = db.search_terms_fts("planner")
        assert len(results) == 1
        assert results[0]["term"] == "daily planner"

    def test_filters_by_app(self, db: AsoDb, salta_ios: int, salta_android: int):
        db.import_search_terms(
            "com.jnuo.salta",
            "ios",
            "2026-04-01",
            "2026-04-30",
            [{"term": "ios only term", "impressions": 100}],
        )
        db.import_search_terms(
            "com.jnuo.salta",
            "android",
            "2026-04-01",
            "2026-04-30",
            [{"term": "android only term", "impressions": 100}],
        )
        ios_results = db.search_terms_fts("term", "com.jnuo.salta", "ios")
        terms = {r["term"] for r in ios_results}
        assert "ios only term" in terms
        assert "android only term" not in terms

    def test_returns_empty_for_no_match(self, db: AsoDb, salta_ios: int):
        db.import_search_terms(
            "com.jnuo.salta",
            "ios",
            "2026-04-01",
            "2026-04-30",
            [{"term": "planner", "impressions": 100}],
        )
        assert db.search_terms_fts("nonexistent xyz") == []


class TestReviewsFts:
    def test_finds_in_body(self, db: AsoDb, salta_ios: int):
        db.import_reviews(
            "com.jnuo.salta",
            "ios",
            "2026-04-01",
            "2026-04-30",
            [
                {
                    "review_id": "r1",
                    "rating": 1,
                    "title": "bug",
                    "body": "App crashes on Xiaomi keyboard",
                    "posted_at": "2026-04-15",
                }
            ],
        )
        results = db.search_reviews_fts("crashes")
        assert len(results) == 1
        assert results[0]["rating"] == 1


# ── Stats ───────────────────────────────────────────────────────────────


class TestStats:
    def test_empty_db_has_no_apps(self, db: AsoDb):
        result = db.stats()
        assert result["apps"] == []
        assert result["total_snapshots"] == 0

    def test_aggregates_across_report_types(self, db: AsoDb, salta_ios: int):
        db.import_search_terms(
            "com.jnuo.salta", "ios", "2026-04-01", "2026-04-30",
            [{"term": "x", "impressions": 1}],
        )
        db.import_metadata(
            "com.jnuo.salta", "ios", "2026-05-04",
            [{"locale": "en-US", "title": "Salta"}],
        )
        result = db.stats()
        assert len(result["apps"]) == 1
        per_type = result["apps"][0]["by_report_type"]
        assert per_type["search_terms"]["snapshots"] == 1
        assert per_type["metadata"]["snapshots"] == 1
        assert per_type["reviews"]["snapshots"] == 0
        assert result["total_snapshots"] == 2
