-- GSC Intelligence Database Schema

CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    product TEXT NOT NULL,
    date_added TEXT DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    pulled_at TEXT DEFAULT (datetime('now')),
    row_count INTEGER DEFAULT 0,
    UNIQUE(site_id, start_date, end_date)
);

CREATE TABLE IF NOT EXISTS performance (
    id INTEGER PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    query TEXT NOT NULL,
    page TEXT NOT NULL,
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr REAL DEFAULT 0.0,
    position REAL DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS idx_perf_snapshot ON performance(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_perf_query_page ON performance(query, page);

CREATE VIRTUAL TABLE IF NOT EXISTS performance_fts USING fts5(
    query, page, content=performance, content_rowid=id
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS perf_ai AFTER INSERT ON performance BEGIN
    INSERT INTO performance_fts(rowid, query, page) VALUES (new.id, new.query, new.page);
END;

CREATE TRIGGER IF NOT EXISTS perf_ad AFTER DELETE ON performance BEGIN
    INSERT INTO performance_fts(performance_fts, rowid, query, page) VALUES ('delete', old.id, old.query, old.page);
END;
