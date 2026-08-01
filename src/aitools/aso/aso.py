"""ASO Intelligence — SQLite storage, trend computation, and search for App Store / Play Store data.

Mirrors the GscDb pattern: register apps once, import periodic snapshots
(search terms, metadata, reviews, rankings), then compute trends and run FTS5
search across stored facts.
"""

import sqlite3
from pathlib import Path
from typing import Optional

SCHEMA_PATH = Path(__file__).parent / "aso_schema.sql"
DEFAULT_DB = Path.home() / "Documents" / "code" / "RoboPM" / "scripts" / "data" / "aso.db"

VALID_PLATFORMS = ("ios", "android")
VALID_REPORT_TYPES = ("search_terms", "metadata", "reviews", "rankings")


class AsoDb:
    """SQLite wrapper for ASO intelligence data."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_schema()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _ensure_schema(self):
        schema = SCHEMA_PATH.read_text()
        self.conn.executescript(schema)

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Apps ───────────────────────────────────────────────────────────

    def add_app(
        self, bundle_id: str, product: str, platform: str, country: str = "us"
    ) -> int:
        """Register an app or return its existing id.

        bundle_id should be the App Store bundle id (e.g. com.jnuo.salta) or
        the Google Play package name. The (bundle_id, platform, country) triple
        is unique — same app on iOS + Android registers as two rows.
        """
        if platform not in VALID_PLATFORMS:
            raise ValueError(f"platform must be one of {VALID_PLATFORMS}, got {platform!r}")
        country = country.lower()
        existing = self.conn.execute(
            "SELECT id FROM apps WHERE bundle_id = ? AND platform = ? AND country = ?",
            (bundle_id, platform, country),
        ).fetchone()
        if existing:
            return existing["id"]
        cursor = self.conn.execute(
            "INSERT INTO apps (bundle_id, product, platform, country) VALUES (?, ?, ?, ?)",
            (bundle_id, product, platform, country),
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_apps(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM apps ORDER BY product, platform, country"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_app(
        self, bundle_id: str, platform: str, country: str = "us"
    ) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM apps WHERE bundle_id = ? AND platform = ? AND country = ?",
            (bundle_id, platform, country.lower()),
        ).fetchone()
        return dict(row) if row else None

    # ── Snapshots ──────────────────────────────────────────────────────

    def _open_snapshot(
        self,
        app_id: int,
        report_type: str,
        start_date: str,
        end_date: str,
        row_count: int,
    ) -> int:
        """Get-or-create a snapshot row. If exists, clears its facts and updates pulled_at."""
        if report_type not in VALID_REPORT_TYPES:
            raise ValueError(
                f"report_type must be one of {VALID_REPORT_TYPES}, got {report_type!r}"
            )
        existing = self.conn.execute(
            "SELECT id FROM snapshots "
            "WHERE app_id = ? AND report_type = ? AND start_date = ? AND end_date = ?",
            (app_id, report_type, start_date, end_date),
        ).fetchone()
        if existing:
            snap_id = existing["id"]
            self._clear_snapshot_facts(snap_id, report_type)
            self.conn.execute(
                "UPDATE snapshots SET pulled_at = datetime('now'), row_count = ? WHERE id = ?",
                (row_count, snap_id),
            )
            return snap_id
        cursor = self.conn.execute(
            "INSERT INTO snapshots (app_id, report_type, start_date, end_date, row_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (app_id, report_type, start_date, end_date, row_count),
        )
        return cursor.lastrowid

    def _clear_snapshot_facts(self, snapshot_id: int, report_type: str):
        """Delete fact rows for a snapshot when re-importing."""
        table = {
            "search_terms": "search_terms",
            "metadata": "metadata_snapshots",
            "reviews": "reviews",
            "rankings": "rankings",
        }[report_type]
        self.conn.execute(f"DELETE FROM {table} WHERE snapshot_id = ?", (snapshot_id,))

    # ── Import: search terms ───────────────────────────────────────────

    def import_search_terms(
        self,
        bundle_id: str,
        platform: str,
        start_date: str,
        end_date: str,
        rows: list[dict],
        country: str = "us",
    ) -> dict:
        """Import search-term rows from ASC Analytics or Play Console for a period.

        Each row should have: term, impressions, taps, conversions, position (any may be missing).
        """
        app = self.get_app(bundle_id, platform, country)
        if not app:
            raise ValueError(
                f"App not registered: {bundle_id} on {platform} ({country}). Add it first."
            )
        snap_id = self._open_snapshot(
            app["id"], "search_terms", start_date, end_date, len(rows)
        )
        fact_rows = [
            (
                snap_id,
                str(r.get("term", "")),
                int(r.get("impressions", 0)),
                int(r.get("taps", 0)),
                int(r.get("conversions", 0)),
                float(r.get("position", 0.0)),
            )
            for r in rows
        ]
        self.conn.executemany(
            "INSERT INTO search_terms (snapshot_id, term, impressions, taps, conversions, position) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            fact_rows,
        )
        self.conn.commit()
        return {
            "snapshot_id": snap_id,
            "app": f"{bundle_id} ({platform}/{country})",
            "report_type": "search_terms",
            "period": f"{start_date} → {end_date}",
            "rows_imported": len(fact_rows),
        }

    # ── Import: metadata ───────────────────────────────────────────────

    def import_metadata(
        self,
        bundle_id: str,
        platform: str,
        snapshot_date: str,
        locales: list[dict],
        country: str = "us",
    ) -> dict:
        """Import a metadata snapshot — list of per-locale dicts.

        Each locale dict should have: locale, title, subtitle, keywords_field,
        description, promotional_text, short_description (any may be missing).
        snapshot_date is used as both start_date and end_date (point-in-time).
        """
        app = self.get_app(bundle_id, platform, country)
        if not app:
            raise ValueError(
                f"App not registered: {bundle_id} on {platform} ({country}). Add it first."
            )
        snap_id = self._open_snapshot(
            app["id"], "metadata", snapshot_date, snapshot_date, len(locales)
        )
        fact_rows = [
            (
                snap_id,
                str(loc.get("locale", "")),
                loc.get("title"),
                loc.get("subtitle"),
                loc.get("keywords_field"),
                loc.get("description"),
                loc.get("promotional_text"),
                loc.get("short_description"),
            )
            for loc in locales
        ]
        self.conn.executemany(
            "INSERT INTO metadata_snapshots (snapshot_id, locale, title, subtitle, "
            "keywords_field, description, promotional_text, short_description) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            fact_rows,
        )
        self.conn.commit()
        return {
            "snapshot_id": snap_id,
            "app": f"{bundle_id} ({platform}/{country})",
            "report_type": "metadata",
            "snapshot_date": snapshot_date,
            "locales_imported": len(fact_rows),
        }

    # ── Import: reviews ────────────────────────────────────────────────

    def import_reviews(
        self,
        bundle_id: str,
        platform: str,
        start_date: str,
        end_date: str,
        rows: list[dict],
        country: str = "us",
    ) -> dict:
        """Import review rows for a period.

        Each row should have: review_id, rating, title, body, version, country,
        locale, posted_at.
        """
        app = self.get_app(bundle_id, platform, country)
        if not app:
            raise ValueError(
                f"App not registered: {bundle_id} on {platform} ({country}). Add it first."
            )
        snap_id = self._open_snapshot(
            app["id"], "reviews", start_date, end_date, len(rows)
        )
        fact_rows = [
            (
                snap_id,
                r.get("review_id"),
                int(r["rating"]) if r.get("rating") is not None else None,
                r.get("title"),
                r.get("body"),
                r.get("version"),
                r.get("country"),
                r.get("locale"),
                r.get("posted_at"),
            )
            for r in rows
        ]
        self.conn.executemany(
            "INSERT INTO reviews (snapshot_id, review_id, rating, title, body, "
            "version, country, locale, posted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            fact_rows,
        )
        self.conn.commit()
        return {
            "snapshot_id": snap_id,
            "app": f"{bundle_id} ({platform}/{country})",
            "report_type": "reviews",
            "period": f"{start_date} → {end_date}",
            "rows_imported": len(fact_rows),
        }

    # ── Import: rankings ───────────────────────────────────────────────

    def import_rankings(
        self,
        bundle_id: str,
        platform: str,
        snapshot_date: str,
        rows: list[dict],
        country: str = "us",
    ) -> dict:
        """Import a keyword-ranking snapshot.

        Each row should have: keyword, rank, country (optional, falls back to app country).
        """
        app = self.get_app(bundle_id, platform, country)
        if not app:
            raise ValueError(
                f"App not registered: {bundle_id} on {platform} ({country}). Add it first."
            )
        snap_id = self._open_snapshot(
            app["id"], "rankings", snapshot_date, snapshot_date, len(rows)
        )
        fact_rows = [
            (
                snap_id,
                str(r["keyword"]),
                int(r["rank"]) if r.get("rank") is not None else None,
                r.get("country", country),
            )
            for r in rows
        ]
        self.conn.executemany(
            "INSERT INTO rankings (snapshot_id, keyword, rank, country) "
            "VALUES (?, ?, ?, ?)",
            fact_rows,
        )
        self.conn.commit()
        return {
            "snapshot_id": snap_id,
            "app": f"{bundle_id} ({platform}/{country})",
            "report_type": "rankings",
            "snapshot_date": snapshot_date,
            "rows_imported": len(fact_rows),
        }

    # ── Trends: search terms ───────────────────────────────────────────

    def compute_search_term_trends(
        self,
        bundle_id: str,
        platform: str,
        country: str = "us",
        limit: int = 50,
    ) -> dict:
        """Compare latest two search-term snapshots for an app.

        Classifies terms as rising (impressions up >20%), declining (down >20%),
        new (in current only), or lost (in previous only).
        """
        app = self.get_app(bundle_id, platform, country)
        if not app:
            raise ValueError(f"App not found: {bundle_id} ({platform}/{country})")

        snapshots = self.conn.execute(
            "SELECT id, start_date, end_date, row_count FROM snapshots "
            "WHERE app_id = ? AND report_type = 'search_terms' "
            "ORDER BY end_date DESC, pulled_at DESC LIMIT 2",
            (app["id"],),
        ).fetchall()

        if len(snapshots) == 0:
            return {"error": "No search-term snapshots found", "app": app}

        if len(snapshots) == 1:
            snap = snapshots[0]
            top = self.conn.execute(
                "SELECT term, impressions, taps, conversions, position "
                "FROM search_terms WHERE snapshot_id = ? "
                "ORDER BY impressions DESC LIMIT ?",
                (snap["id"], limit),
            ).fetchall()
            return {
                "app": app,
                "mode": "single_snapshot",
                "period": f"{snap['start_date']} → {snap['end_date']}",
                "total_rows": snap["row_count"],
                "top_terms": [dict(r) for r in top],
            }

        current, previous = snapshots[0], snapshots[1]

        rising = self.conn.execute(
            """
            SELECT c.term,
                   c.impressions AS imp_now, p.impressions AS imp_prev,
                   c.taps AS taps_now, p.taps AS taps_prev,
                   c.conversions AS conv_now, p.conversions AS conv_prev,
                   ROUND((c.impressions - p.impressions) * 100.0 / MAX(p.impressions, 1), 1) AS imp_change_pct
            FROM search_terms c
            JOIN search_terms p ON c.term = p.term
            WHERE c.snapshot_id = ? AND p.snapshot_id = ?
              AND c.impressions > p.impressions * 1.2
            ORDER BY (c.impressions - p.impressions) DESC
            LIMIT ?
            """,
            (current["id"], previous["id"], limit),
        ).fetchall()

        declining = self.conn.execute(
            """
            SELECT c.term,
                   c.impressions AS imp_now, p.impressions AS imp_prev,
                   c.taps AS taps_now, p.taps AS taps_prev,
                   c.conversions AS conv_now, p.conversions AS conv_prev,
                   ROUND((c.impressions - p.impressions) * 100.0 / MAX(p.impressions, 1), 1) AS imp_change_pct
            FROM search_terms c
            JOIN search_terms p ON c.term = p.term
            WHERE c.snapshot_id = ? AND p.snapshot_id = ?
              AND c.impressions < p.impressions * 0.8
            ORDER BY (p.impressions - c.impressions) DESC
            LIMIT ?
            """,
            (current["id"], previous["id"], limit),
        ).fetchall()

        new = self.conn.execute(
            """
            SELECT c.term, c.impressions, c.taps, c.conversions, c.position
            FROM search_terms c
            LEFT JOIN search_terms p ON c.term = p.term AND p.snapshot_id = ?
            WHERE c.snapshot_id = ? AND p.id IS NULL
            ORDER BY c.impressions DESC
            LIMIT ?
            """,
            (previous["id"], current["id"], limit),
        ).fetchall()

        lost = self.conn.execute(
            """
            SELECT p.term, p.impressions, p.taps, p.conversions, p.position
            FROM search_terms p
            LEFT JOIN search_terms c ON p.term = c.term AND c.snapshot_id = ?
            WHERE p.snapshot_id = ? AND c.id IS NULL
            ORDER BY p.impressions DESC
            LIMIT ?
            """,
            (current["id"], previous["id"], limit),
        ).fetchall()

        return {
            "app": app,
            "mode": "comparison",
            "current_period": f"{current['start_date']} → {current['end_date']}",
            "previous_period": f"{previous['start_date']} → {previous['end_date']}",
            "rising": [dict(r) for r in rising],
            "declining": [dict(r) for r in declining],
            "new": [dict(r) for r in new],
            "lost": [dict(r) for r in lost],
            "counts": {
                "rising": len(rising),
                "declining": len(declining),
                "new": len(new),
                "lost": len(lost),
            },
        }

    # ── Trends: rankings ───────────────────────────────────────────────

    def compute_ranking_trends(
        self,
        bundle_id: str,
        platform: str,
        country: str = "us",
        limit: int = 50,
    ) -> dict:
        """Compare latest two rankings snapshots.

        Lower rank number is better — rising = rank decreased, declining = rank increased.
        """
        app = self.get_app(bundle_id, platform, country)
        if not app:
            raise ValueError(f"App not found: {bundle_id} ({platform}/{country})")

        snapshots = self.conn.execute(
            "SELECT id, start_date FROM snapshots "
            "WHERE app_id = ? AND report_type = 'rankings' "
            "ORDER BY start_date DESC, pulled_at DESC LIMIT 2",
            (app["id"],),
        ).fetchall()

        if len(snapshots) < 2:
            return {
                "error": "Need at least 2 ranking snapshots for trend comparison",
                "app": app,
                "snapshots_available": len(snapshots),
            }

        current, previous = snapshots[0], snapshots[1]

        rising = self.conn.execute(
            """
            SELECT c.keyword, c.rank AS rank_now, p.rank AS rank_prev,
                   (p.rank - c.rank) AS rank_delta
            FROM rankings c
            JOIN rankings p ON c.keyword = p.keyword
            WHERE c.snapshot_id = ? AND p.snapshot_id = ?
              AND c.rank IS NOT NULL AND p.rank IS NOT NULL
              AND c.rank < p.rank
            ORDER BY (p.rank - c.rank) DESC
            LIMIT ?
            """,
            (current["id"], previous["id"], limit),
        ).fetchall()

        declining = self.conn.execute(
            """
            SELECT c.keyword, c.rank AS rank_now, p.rank AS rank_prev,
                   (c.rank - p.rank) AS rank_delta
            FROM rankings c
            JOIN rankings p ON c.keyword = p.keyword
            WHERE c.snapshot_id = ? AND p.snapshot_id = ?
              AND c.rank IS NOT NULL AND p.rank IS NOT NULL
              AND c.rank > p.rank
            ORDER BY (c.rank - p.rank) DESC
            LIMIT ?
            """,
            (current["id"], previous["id"], limit),
        ).fetchall()

        return {
            "app": app,
            "mode": "comparison",
            "current_date": current["start_date"],
            "previous_date": previous["start_date"],
            "rising": [dict(r) for r in rising],
            "declining": [dict(r) for r in declining],
            "counts": {"rising": len(rising), "declining": len(declining)},
        }

    # ── Search ─────────────────────────────────────────────────────────

    def search_terms_fts(
        self,
        text: str,
        bundle_id: Optional[str] = None,
        platform: Optional[str] = None,
        country: str = "us",
        limit: int = 30,
    ) -> list[dict]:
        """FTS5 search over search-term facts. Optionally scope to one app."""
        if bundle_id and platform:
            app = self.get_app(bundle_id, platform, country)
            if not app:
                return []
            rows = self.conn.execute(
                """
                SELECT st.term, st.impressions, st.taps, st.conversions, st.position,
                       s.start_date, s.end_date, a.product, a.platform, a.country
                FROM search_terms_fts fts
                JOIN search_terms st ON st.id = fts.rowid
                JOIN snapshots s ON s.id = st.snapshot_id
                JOIN apps a ON a.id = s.app_id
                WHERE search_terms_fts MATCH ? AND a.id = ?
                ORDER BY st.impressions DESC
                LIMIT ?
                """,
                (text, app["id"], limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT st.term, st.impressions, st.taps, st.conversions, st.position,
                       s.start_date, s.end_date, a.product, a.platform, a.country
                FROM search_terms_fts fts
                JOIN search_terms st ON st.id = fts.rowid
                JOIN snapshots s ON s.id = st.snapshot_id
                JOIN apps a ON a.id = s.app_id
                WHERE search_terms_fts MATCH ?
                ORDER BY st.impressions DESC
                LIMIT ?
                """,
                (text, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def search_reviews_fts(
        self,
        text: str,
        bundle_id: Optional[str] = None,
        platform: Optional[str] = None,
        country: str = "us",
        limit: int = 30,
    ) -> list[dict]:
        """FTS5 search over review titles + bodies. Optionally scope to one app."""
        if bundle_id and platform:
            app = self.get_app(bundle_id, platform, country)
            if not app:
                return []
            rows = self.conn.execute(
                """
                SELECT r.review_id, r.rating, r.title, r.body, r.version,
                       r.country, r.locale, r.posted_at,
                       a.product, a.platform
                FROM reviews_fts fts
                JOIN reviews r ON r.id = fts.rowid
                JOIN snapshots s ON s.id = r.snapshot_id
                JOIN apps a ON a.id = s.app_id
                WHERE reviews_fts MATCH ? AND a.id = ?
                ORDER BY r.posted_at DESC
                LIMIT ?
                """,
                (text, app["id"], limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT r.review_id, r.rating, r.title, r.body, r.version,
                       r.country, r.locale, r.posted_at,
                       a.product, a.platform
                FROM reviews_fts fts
                JOIN reviews r ON r.id = fts.rowid
                JOIN snapshots s ON s.id = r.snapshot_id
                JOIN apps a ON a.id = s.app_id
                WHERE reviews_fts MATCH ?
                ORDER BY r.posted_at DESC
                LIMIT ?
                """,
                (text, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Stats ──────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Per-app summary across all report types."""
        apps = self.list_apps()
        result = {"apps": [], "total_snapshots": 0}

        for app in apps:
            per_type = {}
            for rt in VALID_REPORT_TYPES:
                count = self.conn.execute(
                    "SELECT COUNT(*) AS c FROM snapshots WHERE app_id = ? AND report_type = ?",
                    (app["id"], rt),
                ).fetchone()["c"]
                latest = self.conn.execute(
                    "SELECT start_date, end_date, pulled_at FROM snapshots "
                    "WHERE app_id = ? AND report_type = ? "
                    "ORDER BY end_date DESC, pulled_at DESC LIMIT 1",
                    (app["id"], rt),
                ).fetchone()
                per_type[rt] = {
                    "snapshots": count,
                    "latest_period": (
                        f"{latest['start_date']} → {latest['end_date']}"
                        if latest
                        else None
                    ),
                    "last_pulled": latest["pulled_at"] if latest else None,
                }
                result["total_snapshots"] += count

            result["apps"].append(
                {
                    "product": app["product"],
                    "bundle_id": app["bundle_id"],
                    "platform": app["platform"],
                    "country": app["country"],
                    "by_report_type": per_type,
                }
            )

        return result

    # ── Keyword candidates (DataForSEO validation runs) ────────────────

    def save_candidates(self, app_id: int, candidates: list[dict]) -> int:
        """Persist a validation run. Re-running the same day overwrites that day's rows.

        Each candidate is the dict form of :class:`validate.Candidate`. Returns the
        number of rows written.
        """
        import json as _json

        rows = [
            (
                app_id,
                c["keyword"],
                c.get("cluster"),
                c.get("search_volume"),
                c.get("volume_source"),
                c.get("difficulty"),
                c.get("our_rank"),
                _json.dumps(c.get("top_apps")) if c.get("top_apps") else None,
                c["verdict"],
                c.get("reason"),
            )
            for c in candidates
        ]
        self.conn.executemany(
            "INSERT INTO keyword_candidates "
            "(app_id, keyword, cluster, search_volume, volume_source, difficulty, "
            " our_rank, top_apps, verdict, reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(app_id, keyword, pulled_on) DO UPDATE SET "
            "  cluster=excluded.cluster, search_volume=excluded.search_volume, "
            "  volume_source=excluded.volume_source, difficulty=excluded.difficulty, "
            "  our_rank=excluded.our_rank, top_apps=excluded.top_apps, "
            "  verdict=excluded.verdict, reason=excluded.reason",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def list_candidates(
        self, app_id: int, verdict: Optional[str] = None, pulled_on: Optional[str] = None
    ) -> list[dict]:
        """Read back a validation run, newest day first unless a date is given."""
        sql = "SELECT * FROM keyword_candidates WHERE app_id = ?"
        params: list = [app_id]
        if verdict:
            sql += " AND verdict = ?"
            params.append(verdict)
        if pulled_on:
            sql += " AND pulled_on = ?"
            params.append(pulled_on)
        sql += " ORDER BY pulled_on DESC, difficulty ASC, search_volume DESC"
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]
