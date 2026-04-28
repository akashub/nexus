from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from nexus.models import Concept, Conversation, Edge

DB_DIR = Path.home() / ".nexus"
DB_PATH = DB_DIR / "nexus.db"
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"

_PRAGMAS = [
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA busy_timeout=5000",
    "PRAGMA foreign_keys=ON",
]


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    for pragma in _PRAGMAS:
        conn.execute(pragma)
    return conn


def init_db(db_path: Path | None = None) -> None:
    conn = get_connection(db_path)
    try:
        _run_migrations(conn)
    finally:
        conn.close()


def _run_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _migrations "
        "(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, "
        "applied_at TEXT DEFAULT (datetime('now')))"
    )
    applied = {row["name"] for row in conn.execute("SELECT name FROM _migrations")}
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if sql_file.name in applied:
            continue
        conn.executescript(sql_file.read_text())
        conn.execute("INSERT INTO _migrations (name) VALUES (?)", (sql_file.name,))
        conn.commit()


def add_concept(
    conn: sqlite3.Connection,
    name: str,
    *,
    description: str | None = None,
    summary: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    source: str = "manual",
    embedding: bytes | None = None,
    notes: str | None = None,
    setup: str | None = None,
) -> Concept:
    cid = str(uuid.uuid4())
    tags_json = json.dumps(tags or [])
    conn.execute(
        "INSERT INTO concepts (id, name, description, summary, category, tags, "
        "source, embedding, notes, setup) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (cid, name, description, summary, category, tags_json, source, embedding, notes, setup),
    )
    conn.commit()
    return get_concept(conn, cid)


def get_concept(conn: sqlite3.Connection, id_or_name: str) -> Concept | None:
    row = conn.execute(
        "SELECT * FROM concepts WHERE id = ? OR name = ? COLLATE NOCASE",
        (id_or_name, id_or_name),
    ).fetchone()
    return Concept.from_row(dict(row)) if row else None


def list_concepts(
    conn: sqlite3.Connection,
    *,
    limit: int = 100,
    category: str | None = None,
) -> list[Concept]:
    query = "SELECT * FROM concepts"
    params: list = []
    if category:
        query += " WHERE category = ?"
        params.append(category)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    return [Concept.from_row(dict(r)) for r in rows]


def update_concept(conn: sqlite3.Connection, cid: str, **fields) -> Concept | None:
    if "tags" in fields and isinstance(fields["tags"], list):
        fields["tags"] = json.dumps(fields["tags"])
    sets = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [cid]
    conn.execute(
        f"UPDATE concepts SET {sets}, updated_at = datetime('now') WHERE id = ?",
        vals,
    )
    conn.commit()
    return get_concept(conn, cid)


def delete_concept(conn: sqlite3.Connection, cid: str) -> bool:
    cur = conn.execute("DELETE FROM concepts WHERE id = ?", (cid,))
    conn.commit()
    return cur.rowcount > 0


def add_edge(
    conn: sqlite3.Connection,
    source_id: str,
    target_id: str,
    relationship: str,
    *,
    description: str | None = None,
    weight: float = 1.0,
) -> Edge:
    eid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO edges (id, source_id, target_id, relationship, description, weight) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (eid, source_id, target_id, relationship, description, weight),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM edges WHERE id = ?", (eid,)).fetchone()
    return Edge.from_row(dict(row))


def get_edges(conn: sqlite3.Connection, concept_id: str) -> list[Edge]:
    rows = conn.execute(
        "SELECT * FROM edges WHERE source_id = ? OR target_id = ?",
        (concept_id, concept_id),
    ).fetchall()
    return [Edge.from_row(dict(r)) for r in rows]


def get_all_edges(conn: sqlite3.Connection, limit: int = 5000) -> list[Edge]:
    rows = conn.execute("SELECT * FROM edges LIMIT ?", (limit,)).fetchall()
    return [Edge.from_row(dict(r)) for r in rows]


def count_edges(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) as cnt FROM edges").fetchone()
    return row["cnt"]


def delete_edge(conn: sqlite3.Connection, eid: str) -> bool:
    cur = conn.execute("DELETE FROM edges WHERE id = ?", (eid,))
    conn.commit()
    return cur.rowcount > 0


def add_conversation(
    conn: sqlite3.Connection,
    question: str,
    answer: str,
    concept_ids: list[str] | None = None,
) -> Conversation:
    cid = str(uuid.uuid4())
    related = json.dumps(concept_ids or [])
    conn.execute(
        "INSERT INTO conversations (id, question, answer, related_concepts) "
        "VALUES (?, ?, ?, ?)",
        (cid, question, answer, related),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM conversations WHERE id = ?", (cid,)).fetchone()
    return Conversation.from_row(dict(row))


def search_fts(conn: sqlite3.Connection, query: str) -> list[Concept]:
    try:
        rows = conn.execute(
            "SELECT c.* FROM concepts_fts f "
            "JOIN concepts c ON c.rowid = f.rowid "
            "WHERE concepts_fts MATCH ? ORDER BY rank",
            (query,),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = conn.execute(
            "SELECT * FROM concepts WHERE name LIKE ? OR description LIKE ?",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
    return [Concept.from_row(dict(r)) for r in rows]
