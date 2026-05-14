-- Allow same concept name in multiple projects.
-- Changes UNIQUE(name) to UNIQUE(name, project_id).

-- 1. Rebuild concepts table without inline UNIQUE on name
CREATE TABLE concepts_new (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE,
    description TEXT,
    summary TEXT,
    category TEXT,
    tags TEXT DEFAULT '[]',
    source TEXT DEFAULT 'manual',
    embedding BLOB,
    notes TEXT,
    setup TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    quickstart TEXT,
    doc_url TEXT,
    context7_id TEXT,
    enrich_status TEXT,
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    setup_commands TEXT,
    config_files TEXT,
    semantic_group TEXT,
    layer TEXT DEFAULT 'project',
    usage_summary TEXT,
    UNIQUE(name, project_id)
);

INSERT INTO concepts_new SELECT * FROM concepts;

-- 2. Drop old triggers, table, rename
DROP TRIGGER IF EXISTS concepts_ai;
DROP TRIGGER IF EXISTS concepts_ad;
DROP TRIGGER IF EXISTS concepts_au;
DROP TABLE concepts;
ALTER TABLE concepts_new RENAME TO concepts;

-- 3. Recreate indexes
CREATE INDEX IF NOT EXISTS idx_concepts_project ON concepts(project_id);

-- 4. Recreate FTS triggers
CREATE TRIGGER concepts_ai AFTER INSERT ON concepts BEGIN
    INSERT INTO concepts_fts(rowid, name, description, summary, notes, tags)
    VALUES (new.rowid, new.name, new.description, new.summary, new.notes, new.tags);
END;

CREATE TRIGGER concepts_ad AFTER DELETE ON concepts BEGIN
    INSERT INTO concepts_fts(concepts_fts, rowid, name, description, summary, notes, tags)
    VALUES ('delete', old.rowid, old.name, old.description, old.summary, old.notes, old.tags);
END;

CREATE TRIGGER concepts_au AFTER UPDATE ON concepts BEGIN
    INSERT INTO concepts_fts(concepts_fts, rowid, name, description, summary, notes, tags)
    VALUES ('delete', old.rowid, old.name, old.description, old.summary, old.notes, old.tags);
    INSERT INTO concepts_fts(rowid, name, description, summary, notes, tags)
    VALUES (new.rowid, new.name, new.description, new.summary, new.notes, new.tags);
END;
