"""GSC Intelligence — SQLite storage, trend computation, and search for Google Search Console data."""

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

SCHEMA_PATH = Path(__file__).parent / "gsc_schema.sql"
DEFAULT_DB = Path.home() / "Documents" / "code" / "RoboPM" / "scripts" / "data" / "gsc.db"


class GscDb:
    """SQLite wrapper for GSC intelligence data."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB
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

    # ── Sites ──────────────────────────────────────────────────────────

    def add_site(self, url: str, product: str) -> int:
        """Add or get a site. Returns site ID."""
        row = self.conn.execute("SELECT id FROM sites WHERE url = ?", (url,)).fetchone()
        if row:
            return row["id"]
        cursor = self.conn.execute(
            "INSERT INTO sites (url, product) VALUES (?, ?)", (url, product)
        )
        self.conn.commit()
        return cursor.lastrowid

    def list_sites(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM sites ORDER BY product").fetchall()
        return [dict(r) for r in rows]

    # ── Import ─────────────────────────────────────────────────────────

    def import_data(
        self, site_url: str, start_date: str, end_date: str, rows: list[dict]
    ) -> dict:
        """Import GSC performance rows for a site+period. Returns summary."""
        site = self.conn.execute(
            "SELECT id FROM sites WHERE url = ?", (site_url,)
        ).fetchone()
        if not site:
            raise ValueError(f"Site not registered: {site_url}. Add it first.")

        site_id = site["id"]

        # Check for existing snapshot with same range
        existing = self.conn.execute(
            "SELECT id FROM snapshots WHERE site_id = ? AND start_date = ? AND end_date = ?",
            (site_id, start_date, end_date),
        ).fetchone()

        if existing:
            # Delete old data and re-import
            snap_id = existing["id"]
            self.conn.execute("DELETE FROM performance WHERE snapshot_id = ?", (snap_id,))
            self.conn.execute(
                "UPDATE snapshots SET pulled_at = datetime('now'), row_count = ? WHERE id = ?",
                (len(rows), snap_id),
            )
        else:
            cursor = self.conn.execute(
                "INSERT INTO snapshots (site_id, start_date, end_date, row_count) VALUES (?, ?, ?, ?)",
                (site_id, start_date, end_date, len(rows)),
            )
            snap_id = cursor.lastrowid

        # Bulk insert performance rows
        perf_rows = []
        for r in rows:
            perf_rows.append((
                snap_id,
                r.get("query", r.get("keys", [""])[0] if "keys" in r else ""),
                r.get("page", r.get("keys", ["", ""])[1] if "keys" in r and len(r.get("keys", [])) > 1 else ""),
                int(r.get("clicks", 0)),
                int(r.get("impressions", 0)),
                float(r.get("ctr", 0.0)),
                float(r.get("position", 0.0)),
            ))

        self.conn.executemany(
            "INSERT INTO performance (snapshot_id, query, page, clicks, impressions, ctr, position) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            perf_rows,
        )
        self.conn.commit()

        return {
            "snapshot_id": snap_id,
            "site": site_url,
            "period": f"{start_date} → {end_date}",
            "rows_imported": len(perf_rows),
        }

    # ── Trends ─────────────────────────────────────────────────────────

    def compute_trends(self, site_url: str, limit: int = 50) -> dict:
        """Compare latest two snapshots for a site. Returns classified query-page pairs."""
        site = self.conn.execute(
            "SELECT id FROM sites WHERE url = ?", (site_url,)
        ).fetchone()
        if not site:
            raise ValueError(f"Site not found: {site_url}")

        snapshots = self.conn.execute(
            "SELECT id, start_date, end_date, row_count FROM snapshots "
            "WHERE site_id = ? ORDER BY end_date DESC LIMIT 2",
            (site["id"],),
        ).fetchall()

        if len(snapshots) == 0:
            return {"error": "No snapshots found", "site": site_url}

        if len(snapshots) == 1:
            # Only one snapshot — return top performers, no trend comparison
            snap = snapshots[0]
            top = self.conn.execute(
                "SELECT query, page, clicks, impressions, ctr, position "
                "FROM performance WHERE snapshot_id = ? ORDER BY impressions DESC LIMIT ?",
                (snap["id"], limit),
            ).fetchall()
            return {
                "site": site_url,
                "mode": "single_snapshot",
                "period": f"{snap['start_date']} → {snap['end_date']}",
                "total_rows": snap["row_count"],
                "top_queries": [dict(r) for r in top],
            }

        current, previous = snapshots[0], snapshots[1]

        # Rising: impressions up >20%
        rising = self.conn.execute("""
            SELECT c.query, c.page,
                   c.clicks as clicks_now, p.clicks as clicks_prev,
                   c.impressions as imp_now, p.impressions as imp_prev,
                   c.position as pos_now, p.position as pos_prev,
                   ROUND((c.impressions - p.impressions) * 100.0 / MAX(p.impressions, 1), 1) as imp_change_pct
            FROM performance c
            JOIN performance p ON c.query = p.query AND c.page = p.page
            WHERE c.snapshot_id = ? AND p.snapshot_id = ?
              AND c.impressions > p.impressions * 1.2
            ORDER BY (c.impressions - p.impressions) DESC
            LIMIT ?
        """, (current["id"], previous["id"], limit)).fetchall()

        # Declining: impressions down >20%
        declining = self.conn.execute("""
            SELECT c.query, c.page,
                   c.clicks as clicks_now, p.clicks as clicks_prev,
                   c.impressions as imp_now, p.impressions as imp_prev,
                   c.position as pos_now, p.position as pos_prev,
                   ROUND((c.impressions - p.impressions) * 100.0 / MAX(p.impressions, 1), 1) as imp_change_pct
            FROM performance c
            JOIN performance p ON c.query = p.query AND c.page = p.page
            WHERE c.snapshot_id = ? AND p.snapshot_id = ?
              AND c.impressions < p.impressions * 0.8
            ORDER BY (p.impressions - c.impressions) DESC
            LIMIT ?
        """, (current["id"], previous["id"], limit)).fetchall()

        # New: in current but not previous
        new = self.conn.execute("""
            SELECT c.query, c.page, c.clicks, c.impressions, c.ctr, c.position
            FROM performance c
            LEFT JOIN performance p ON c.query = p.query AND c.page = p.page AND p.snapshot_id = ?
            WHERE c.snapshot_id = ? AND p.id IS NULL
            ORDER BY c.impressions DESC
            LIMIT ?
        """, (previous["id"], current["id"], limit)).fetchall()

        # Lost: in previous but not current
        lost = self.conn.execute("""
            SELECT p.query, p.page, p.clicks, p.impressions, p.ctr, p.position
            FROM performance p
            LEFT JOIN performance c ON p.query = c.query AND p.page = c.page AND c.snapshot_id = ?
            WHERE p.snapshot_id = ? AND c.id IS NULL
            ORDER BY p.impressions DESC
            LIMIT ?
        """, (current["id"], previous["id"], limit)).fetchall()

        return {
            "site": site_url,
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

    # ── Search ─────────────────────────────────────────────────────────

    def search(self, text: str, site_url: Optional[str] = None, limit: int = 30) -> list[dict]:
        """FTS5 search over queries and pages. Optionally filter by site."""
        if site_url:
            site = self.conn.execute(
                "SELECT id FROM sites WHERE url = ?", (site_url,)
            ).fetchone()
            if not site:
                return []

            # Get snapshot IDs for this site
            rows = self.conn.execute("""
                SELECT p.query, p.page, p.clicks, p.impressions, p.ctr, p.position,
                       s.start_date, s.end_date, si.product
                FROM performance_fts fts
                JOIN performance p ON p.id = fts.rowid
                JOIN snapshots s ON s.id = p.snapshot_id
                JOIN sites si ON si.id = s.site_id
                WHERE performance_fts MATCH ? AND si.url = ?
                ORDER BY p.impressions DESC
                LIMIT ?
            """, (text, site_url, limit)).fetchall()
        else:
            rows = self.conn.execute("""
                SELECT p.query, p.page, p.clicks, p.impressions, p.ctr, p.position,
                       s.start_date, s.end_date, si.product
                FROM performance_fts fts
                JOIN performance p ON p.id = fts.rowid
                JOIN snapshots s ON s.id = p.snapshot_id
                JOIN sites si ON si.id = s.site_id
                WHERE performance_fts MATCH ?
                ORDER BY p.impressions DESC
                LIMIT ?
            """, (text, limit)).fetchall()

        return [dict(r) for r in rows]

    # ── Stats ──────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Database overview stats."""
        sites = self.list_sites()
        result = {"sites": [], "total_rows": 0, "total_snapshots": 0}

        for site in sites:
            snap_count = self.conn.execute(
                "SELECT COUNT(*) as c FROM snapshots WHERE site_id = ?", (site["id"],)
            ).fetchone()["c"]

            row_count = self.conn.execute(
                "SELECT COALESCE(SUM(row_count), 0) as c FROM snapshots WHERE site_id = ?",
                (site["id"],),
            ).fetchone()["c"]

            latest = self.conn.execute(
                "SELECT start_date, end_date, pulled_at FROM snapshots "
                "WHERE site_id = ? ORDER BY end_date DESC, pulled_at DESC LIMIT 1",
                (site["id"],),
            ).fetchone()

            result["sites"].append({
                "product": site["product"],
                "url": site["url"],
                "snapshots": snap_count,
                "total_rows": row_count,
                "latest_period": f"{latest['start_date']} → {latest['end_date']}" if latest else "none",
                "last_pulled": latest["pulled_at"] if latest else "never",
            })
            result["total_rows"] += row_count
            result["total_snapshots"] += snap_count

        return result
