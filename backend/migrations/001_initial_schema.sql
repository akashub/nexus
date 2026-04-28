-- Nexus initial schema

CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    description TEXT,
    summary TEXT,
    category TEXT,
    tags TEXT DEFAULT '[]',
    source TEXT DEFAULT 'manual',
    embedding BLOB,
    notes TEXT,
    setup TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    relationship TEXT NOT NULL,
    description TEXT,
    weight REAL DEFAULT 1.0,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(source_id, target_id, relationship)
);

CREATE TABLE IF NOT EXISTS resources (
    id TEXT PRIMARY KEY,
    concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    url TEXT,
    title TEXT,
    content_summary TEXT,
    type TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    related_concepts TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now'))
);

-- FTS5 full-text search index
CREATE VIRTUAL TABLE IF NOT EXISTS concepts_fts USING fts5(
    name, description, summary, notes, tags,
    content=concepts, content_rowid=rowid
);

-- Migration tracking
CREATE TABLE IF NOT EXISTS _migrations (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    applied_at TEXT DEFAULT (datetime('now'))
);

-- Auto-sync triggers: keep FTS5 in sync with concepts table

CREATE TRIGGER IF NOT EXISTS concepts_ai AFTER INSERT ON concepts BEGIN
    INSERT INTO concepts_fts(rowid, name, description, summary, notes, tags)
    VALUES (new.rowid, new.name, new.description, new.summary, new.notes, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS concepts_ad AFTER DELETE ON concepts BEGIN
    INSERT INTO concepts_fts(concepts_fts, rowid, name, description, summary, notes, tags)
    VALUES ('delete', old.rowid, old.name, old.description, old.summary, old.notes, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS concepts_au AFTER UPDATE ON concepts BEGIN
    INSERT INTO concepts_fts(concepts_fts, rowid, name, description, summary, notes, tags)
    VALUES ('delete', old.rowid, old.name, old.description, old.summary, old.notes, old.tags);
    INSERT INTO concepts_fts(rowid, name, description, summary, notes, tags)
    VALUES (new.rowid, new.name, new.description, new.summary, new.notes, new.tags);
END;
