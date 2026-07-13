-- ASO Intelligence Database Schema
-- Mirrors gsc_schema.sql pattern: apps + snapshots + facts + FTS5

CREATE TABLE IF NOT EXISTS apps (
    id INTEGER PRIMARY KEY,
    bundle_id TEXT NOT NULL,
    product TEXT NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('ios', 'android')),
    country TEXT NOT NULL DEFAULT 'us',
    date_added TEXT DEFAULT (date('now')),
    UNIQUE(bundle_id, platform, country)
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY,
    app_id INTEGER NOT NULL REFERENCES apps(id),
    report_type TEXT NOT NULL CHECK (report_type IN ('search_terms', 'metadata', 'reviews', 'rankings')),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    pulled_at TEXT DEFAULT (datetime('now')),
    row_count INTEGER DEFAULT 0,
    UNIQUE(app_id, report_type, start_date, end_date)
);

CREATE TABLE IF NOT EXISTS search_terms (
    id INTEGER PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    term TEXT NOT NULL,
    impressions INTEGER DEFAULT 0,
    taps INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    position REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS metadata_snapshots (
    id INTEGER PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    locale TEXT NOT NULL,
    title TEXT,
    subtitle TEXT,
    keywords_field TEXT,
    description TEXT,
    promotional_text TEXT,
    short_description TEXT
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    review_id TEXT,
    rating INTEGER,
    title TEXT,
    body TEXT,
    version TEXT,
    country TEXT,
    locale TEXT,
    posted_at TEXT
);

CREATE TABLE IF NOT EXISTS rankings (
    id INTEGER PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
    keyword TEXT NOT NULL,
    rank INTEGER,
    country TEXT
);

-- Scored keyword candidates from a DataForSEO validation run (see validate.py).
-- One row per keyword per day: re-running the same day overwrites, so a month's
-- cycle leaves exactly one comparable snapshot.
CREATE TABLE IF NOT EXISTS keyword_candidates (
    id INTEGER PRIMARY KEY,
    app_id INTEGER NOT NULL REFERENCES apps(id),
    keyword TEXT NOT NULL,
    cluster TEXT,
    search_volume INTEGER,
    volume_source TEXT,
    difficulty REAL,
    our_rank INTEGER,
    top_apps TEXT,
    verdict TEXT NOT NULL,
    reason TEXT,
    pulled_on TEXT NOT NULL DEFAULT (date('now')),
    UNIQUE(app_id, keyword, pulled_on)
);

CREATE INDEX IF NOT EXISTS idx_kc_app ON keyword_candidates(app_id);
CREATE INDEX IF NOT EXISTS idx_kc_verdict ON keyword_candidates(verdict);
CREATE INDEX IF NOT EXISTS idx_kc_keyword ON keyword_candidates(keyword);

CREATE INDEX IF NOT EXISTS idx_st_snapshot ON search_terms(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_st_term ON search_terms(term);
CREATE INDEX IF NOT EXISTS idx_meta_snapshot ON metadata_snapshots(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_rev_snapshot ON reviews(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_rev_rating ON reviews(rating);
CREATE INDEX IF NOT EXISTS idx_rank_snapshot ON rankings(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_rank_keyword ON rankings(keyword);

-- FTS for search terms (organic traffic discovery)
CREATE VIRTUAL TABLE IF NOT EXISTS search_terms_fts USING fts5(
    term, content=search_terms, content_rowid=id
);

CREATE TRIGGER IF NOT EXISTS st_ai AFTER INSERT ON search_terms BEGIN
    INSERT INTO search_terms_fts(rowid, term) VALUES (new.id, new.term);
END;

CREATE TRIGGER IF NOT EXISTS st_ad AFTER DELETE ON search_terms BEGIN
    INSERT INTO search_terms_fts(search_terms_fts, rowid, term) VALUES ('delete', old.id, old.term);
END;

-- FTS for review bodies (qualitative pattern mining)
CREATE VIRTUAL TABLE IF NOT EXISTS reviews_fts USING fts5(
    title, body, content=reviews, content_rowid=id
);

CREATE TRIGGER IF NOT EXISTS rev_ai AFTER INSERT ON reviews BEGIN
    INSERT INTO reviews_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;

CREATE TRIGGER IF NOT EXISTS rev_ad AFTER DELETE ON reviews BEGIN
    INSERT INTO reviews_fts(reviews_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
END;
