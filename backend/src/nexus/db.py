from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

from nexus.models import Project

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
    conn = sqlite3.connect(str(path), check_same_thread=False)
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
        script = sql_file.read_text()
        conn.executescript(script)
        conn.execute("INSERT INTO _migrations (name) VALUES (?)", (sql_file.name,))
        conn.commit()


# --- Project CRUD ---

def add_project(
    conn: sqlite3.Connection, name: str, *, path: str | None = None,
    description: str | None = None,
) -> Project:
    pid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO projects (id, name, path, description) VALUES (?, ?, ?, ?)",
        (pid, name, path, description),
    )
    conn.commit()
    return get_project(conn, pid)


def get_project(conn: sqlite3.Connection, id_or_name: str) -> Project | None:
    row = conn.execute(
        "SELECT * FROM projects WHERE id = ? OR name = ? COLLATE NOCASE",
        (id_or_name, id_or_name),
    ).fetchone()
    return Project.from_row(dict(row)) if row else None


def get_project_by_path(conn: sqlite3.Connection, path: str) -> Project | None:
    row = conn.execute(
        "SELECT * FROM projects WHERE path = ?", (path,),
    ).fetchone()
    return Project.from_row(dict(row)) if row else None


def list_projects(conn: sqlite3.Connection) -> list[Project]:
    rows = conn.execute(
        "SELECT * FROM projects ORDER BY updated_at DESC",
    ).fetchall()
    return [Project.from_row(dict(r)) for r in rows]


def update_project(conn: sqlite3.Connection, pid: str, **fields) -> Project | None:
    allowed = {"name", "path", "description", "last_scanned_at"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return get_project(conn, pid)
    sets = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [pid]
    conn.execute(
        f"UPDATE projects SET {sets}, updated_at = datetime('now') WHERE id = ?", vals,
    )
    conn.commit()
    return get_project(conn, pid)


def delete_project(conn: sqlite3.Connection, pid: str) -> bool:
    cur = conn.execute("DELETE FROM projects WHERE id = ?", (pid,))
    conn.commit()
    return cur.rowcount > 0


# Re-export concept/edge/conversation functions for backward compat
from nexus.db_concepts import (  # noqa: E402, F401
    add_concept,
    add_conversation,
    add_edge,
    count_concepts,
    count_edges,
    delete_concept,
    delete_edge,
    get_all_edges,
    get_concept,
    get_concept_by_name_and_project,
    get_edges,
    list_concepts,
    list_conversations,
    search_fts,
    update_concept,
)
