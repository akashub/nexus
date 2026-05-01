from __future__ import annotations

import json
import sqlite3
import uuid
from collections import defaultdict
from datetime import datetime

from nexus.models import Concept, Conversation, Edge

_STOP = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "have",
    "has", "had", "do", "does", "did", "will", "would", "could", "should", "may",
    "might", "can", "shall", "to", "of", "in", "for", "on", "with", "at", "by",
    "from", "as", "into", "about", "between", "through", "and", "but", "or", "not",
    "no", "so", "if", "then", "than", "how", "what", "which", "who", "this", "that",
    "it", "its", "my", "your", "i", "you", "he", "she", "we", "they", "me", "him",
    "us", "them", "why", "when", "where", "relate", "related",
})

_UPDATABLE_COLUMNS = frozenset({
    "name", "description", "summary", "category", "tags",
    "source", "embedding", "notes", "quickstart", "doc_url", "context7_id",
    "enrich_status", "project_id", "setup_commands", "config_files",
    "semantic_group",
})


def add_concept(
    conn: sqlite3.Connection, name: str, *, description: str | None = None,
    summary: str | None = None, category: str | None = None,
    tags: list[str] | None = None, source: str = "manual",
    embedding: bytes | None = None, notes: str | None = None,
    quickstart: str | None = None, project_id: str | None = None,
) -> Concept:
    cid = str(uuid.uuid4())
    tags_json = json.dumps(tags or [])
    conn.execute(
        "INSERT INTO concepts (id, name, description, summary, category, tags, "
        "source, embedding, notes, quickstart, project_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (cid, name, description, summary, category, tags_json,
         source, embedding, notes, quickstart, project_id),
    )
    conn.commit()
    return get_concept(conn, cid)


def get_concept(conn: sqlite3.Connection, id_or_name: str) -> Concept | None:
    row = conn.execute(
        "SELECT * FROM concepts WHERE id = ? OR name = ? COLLATE NOCASE",
        (id_or_name, id_or_name),
    ).fetchone()
    return Concept.from_row(dict(row)) if row else None


def get_concept_by_name_and_project(
    conn: sqlite3.Connection, name: str, project_id: str,
) -> Concept | None:
    row = conn.execute(
        "SELECT * FROM concepts WHERE name = ? COLLATE NOCASE AND project_id = ?",
        (name, project_id),
    ).fetchone()
    return Concept.from_row(dict(row)) if row else None


def list_concepts(
    conn: sqlite3.Connection, *, limit: int = 100, category: str | None = None,
    project_id: str | None = None,
) -> list[Concept]:
    query = "SELECT * FROM concepts"
    params: list = []
    clauses: list[str] = []
    if category:
        clauses.append("category = ?")
        params.append(category)
    if project_id:
        clauses.append("project_id = ?")
        params.append(project_id)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    return [Concept.from_row(dict(r)) for r in rows]


def update_concept(conn: sqlite3.Connection, cid: str, **fields) -> Concept | None:
    fields = {k: v for k, v in fields.items() if k in _UPDATABLE_COLUMNS}
    if not fields:
        return get_concept(conn, cid)
    for key in ("tags", "setup_commands", "config_files"):
        if key in fields and isinstance(fields[key], list):
            fields[key] = json.dumps(fields[key])
    sets = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [cid]
    conn.execute(
        f"UPDATE concepts SET {sets}, updated_at = datetime('now') WHERE id = ?", vals,
    )
    conn.commit()
    return get_concept(conn, cid)


def delete_concept(conn: sqlite3.Connection, cid: str) -> bool:
    cur = conn.execute("DELETE FROM concepts WHERE id = ?", (cid,))
    conn.commit()
    return cur.rowcount > 0


def add_edge(
    conn: sqlite3.Connection, source_id: str, target_id: str, relationship: str,
    *, description: str | None = None, weight: float = 1.0,
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
        "SELECT * FROM edges WHERE source_id = ? OR target_id = ?", (concept_id, concept_id),
    ).fetchall()
    return [Edge.from_row(dict(r)) for r in rows]


def get_all_edges(conn: sqlite3.Connection, limit: int = 5000) -> list[Edge]:
    rows = conn.execute("SELECT * FROM edges LIMIT ?", (limit,)).fetchall()
    return [Edge.from_row(dict(r)) for r in rows]


def count_concepts(
    conn: sqlite3.Connection, *, project_id: str | None = None,
    unassigned: bool = False,
) -> int:
    query = "SELECT COUNT(*) as cnt FROM concepts"
    params: list = []
    if project_id:
        query += " WHERE project_id = ?"
        params.append(project_id)
    elif unassigned:
        query += " WHERE project_id IS NULL"
    return conn.execute(query, params).fetchone()["cnt"]


def count_edges(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) as cnt FROM edges").fetchone()["cnt"]


def delete_edge(conn: sqlite3.Connection, eid: str) -> bool:
    cur = conn.execute("DELETE FROM edges WHERE id = ?", (eid,))
    conn.commit()
    return cur.rowcount > 0


def add_conversation(
    conn: sqlite3.Connection, question: str, answer: str,
    concept_ids: list[str] | None = None,
) -> Conversation:
    cid = str(uuid.uuid4())
    related = json.dumps(concept_ids or [])
    conn.execute(
        "INSERT INTO conversations (id, question, answer, related_concepts) "
        "VALUES (?, ?, ?, ?)", (cid, question, answer, related),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM conversations WHERE id = ?", (cid,)).fetchone()
    return Conversation.from_row(dict(row))


def list_conversations(conn: sqlite3.Connection, limit: int = 20) -> list[Conversation]:
    rows = conn.execute(
        "SELECT * FROM conversations ORDER BY created_at DESC LIMIT ?", (limit,),
    ).fetchall()
    return [Conversation.from_row(dict(r)) for r in rows]


def get_journey(
    conn: sqlite3.Connection, *, project_id: str | None = None, days: int = 90,
) -> list[dict]:
    """Return concepts ordered by created_at, grouped by ISO week."""
    query = "SELECT * FROM concepts WHERE created_at >= datetime('now', ?)"
    params: list = [f"-{days} days"]
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    query += " ORDER BY created_at ASC"
    rows = conn.execute(query, params).fetchall()
    concepts = [Concept.from_row(dict(r)) for r in rows]

    weeks: dict[str, list[Concept]] = defaultdict(list)
    for c in concepts:
        dt = datetime.fromisoformat(c.created_at)
        iso_year, iso_week, _ = dt.isocalendar()
        key = f"{iso_year}-W{iso_week:02d}"
        weeks[key].append(c)

    result = []
    for week_key in sorted(weeks):
        year, w = week_key.split("-W")
        week_start = datetime.fromisocalendar(int(year), int(w), 1).date()
        result.append({
            "week": week_key,
            "week_start": week_start.isoformat(),
            "concepts": weeks[week_key],
        })
    return result


def _prepare_fts(query: str) -> str:
    tokens = [w.strip("?.,!;:'\"()") for w in query.lower().split()]
    tokens = [t for t in tokens if t and t not in _STOP and len(t) > 1]
    if not tokens:
        return query
    return " OR ".join(f'"{t}"' for t in tokens)


def search_fts(conn: sqlite3.Connection, query: str) -> list[Concept]:
    fts_q = _prepare_fts(query)
    try:
        rows = conn.execute(
            "SELECT c.* FROM concepts_fts f JOIN concepts c ON c.rowid = f.rowid "
            "WHERE concepts_fts MATCH ? ORDER BY rank", (fts_q,),
        ).fetchall()
    except sqlite3.OperationalError:
        escaped = query.replace("%", "").replace("_", "").replace("[", "").strip()
        if not escaped:
            return []
        rows = conn.execute(
            "SELECT * FROM concepts WHERE name LIKE ? OR description LIKE ?",
            (f"%{escaped}%", f"%{escaped}%"),
        ).fetchall()
    return [Concept.from_row(dict(r)) for r in rows]
