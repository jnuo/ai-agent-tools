"""End-to-end integration tests: full add → import → trends → search → stats flow.

These exercise the public AsoDb API as a real consumer would, with no mocks —
they hit a real SQLite file on a temp path. Fast (<1s) and deterministic.
"""

from pathlib import Path

import pytest

from aitools.aso.aso import AsoDb


@pytest.fixture
def db(tmp_path: Path) -> AsoDb:
    aso = AsoDb(tmp_path / "integration.db")
    yield aso
    aso.close()


def test_full_lifecycle_search_terms(db: AsoDb):
    """Realistic flow: register Salta on iOS + Android, import 2 periods of
    search-term data, compute trends, run FTS search, check stats."""

    # Register both platforms.
    ios_id = db.add_app("com.jnuo.salta", "salta", "ios")
    android_id = db.add_app("com.jnuo.salta", "salta", "android")
    assert ios_id != android_id

    # March data (previous period).
    march = [
        {"term": "daily planner", "impressions": 240, "taps": 50, "conversions": 8},
        {"term": "task manager ai", "impressions": 180, "taps": 30, "conversions": 5},
        {"term": "old keyword", "impressions": 60, "taps": 5, "conversions": 0},
    ]
    db.import_search_terms(
        "com.jnuo.salta", "ios", "2026-03-01", "2026-03-31", march
    )

    # April data (current period) — one rising, one declining, one new, one lost.
    april = [
        {"term": "daily planner", "impressions": 410, "taps": 95, "conversions": 18},  # rising
        {"term": "task manager ai", "impressions": 80, "taps": 12, "conversions": 1},  # declining
        {"term": "ai planner 2026", "impressions": 200, "taps": 40, "conversions": 6},  # new
        # 'old keyword' missing → lost
    ]
    db.import_search_terms(
        "com.jnuo.salta", "ios", "2026-04-01", "2026-04-30", april
    )

    trends = db.compute_search_term_trends("com.jnuo.salta", "ios")
    assert trends["mode"] == "comparison"

    rising_terms = {r["term"] for r in trends["rising"]}
    declining_terms = {r["term"] for r in trends["declining"]}
    new_terms = {r["term"] for r in trends["new"]}
    lost_terms = {r["term"] for r in trends["lost"]}

    assert "daily planner" in rising_terms
    assert "task manager ai" in declining_terms
    assert "ai planner 2026" in new_terms
    assert "old keyword" in lost_terms

    # FTS scoped to ios — Android has no data, results should be ios-only.
    matches = db.search_terms_fts("planner", "com.jnuo.salta", "ios")
    assert any(r["term"] == "daily planner" for r in matches)
    assert all(r["platform"] == "ios" for r in matches)

    # Stats sanity check.
    stats = db.stats()
    assert stats["total_snapshots"] == 2  # two ios search-term snapshots
    salta_apps = [a for a in stats["apps"] if a["product"] == "salta"]
    assert len(salta_apps) == 2  # ios + android registered


def test_metadata_snapshot_overwrite_keeps_one_locale(db: AsoDb):
    """Re-importing metadata for the same date should overwrite, not duplicate."""
    db.add_app("com.jnuo.salta", "salta", "ios")

    db.import_metadata(
        "com.jnuo.salta",
        "ios",
        "2026-05-04",
        [{"locale": "en-US", "title": "v1", "keywords_field": "planner"}],
    )
    db.import_metadata(
        "com.jnuo.salta",
        "ios",
        "2026-05-04",
        [{"locale": "en-US", "title": "v2", "keywords_field": "planner,ai"}],
    )

    rows = db.conn.execute(
        "SELECT title, keywords_field FROM metadata_snapshots"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["title"] == "v2"
    assert rows[0]["keywords_field"] == "planner,ai"


def test_reviews_searchable_after_import(db: AsoDb):
    db.add_app("com.jnuo.salta", "salta", "android")
    db.import_reviews(
        "com.jnuo.salta",
        "android",
        "2026-04-01",
        "2026-04-30",
        [
            {
                "review_id": "r1",
                "rating": 1,
                "title": "Crash on Xiaomi",
                "body": "App crashes when keyboard opens on my Xiaomi phone",
                "version": "1.14.1",
                "posted_at": "2026-04-20T08:00:00Z",
            },
            {
                "review_id": "r2",
                "rating": 5,
                "title": "Love it",
                "body": "Perfect daily planner with AI suggestions",
                "version": "1.14.2",
                "posted_at": "2026-04-22T10:00:00Z",
            },
        ],
    )

    crash_hits = db.search_reviews_fts("crash")
    assert len(crash_hits) == 1
    assert crash_hits[0]["rating"] == 1
    assert "Xiaomi" in crash_hits[0]["body"]

    five_stars = db.search_reviews_fts("planner")
    assert any(r["rating"] == 5 for r in five_stars)


def test_db_is_persistent_across_reopens(tmp_path: Path):
    """Schema and data should survive closing and reopening the connection."""
    db_path = tmp_path / "persist.db"

    # First session: write data.
    a = AsoDb(db_path)
    a.add_app("com.jnuo.salta", "salta", "ios")
    a.import_search_terms(
        "com.jnuo.salta",
        "ios",
        "2026-04-01",
        "2026-04-30",
        [{"term": "persist test", "impressions": 42}],
    )
    a.close()

    # Second session: read it back.
    b = AsoDb(db_path)
    apps = b.list_apps()
    assert len(apps) == 1
    matches = b.search_terms_fts("persist")
    assert len(matches) == 1
    assert matches[0]["impressions"] == 42
    b.close()
