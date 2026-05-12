from __future__ import annotations

import contextlib
import re
import sqlite3
from pathlib import Path

from nexus.scanners import ScannedConcept, ScanResult

EAGLE_MEM_DB = Path.home() / ".eagle-mem" / "memory.db"


def scan_eagle_mem(project_path: Path) -> ScanResult:
    result = ScanResult()
    seen: set[str] = set()
    if not EAGLE_MEM_DB.exists():
        return result
    try:
        conn = sqlite3.connect(str(EAGLE_MEM_DB), timeout=3)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        return result
    project_name = project_path.name
    try:
        _scan_summaries(conn, project_name, result, seen)
        _scan_observations(conn, project_name, result, seen)
        scan_cli_tools(conn, project_name, result, seen)
        _scan_skill_usage(conn, project_name, result, seen)
    except sqlite3.Error:
        pass
    finally:
        conn.close()
    return result


def _scan_summaries(
    conn: sqlite3.Connection, project_name: str,
    result: ScanResult, seen: set[str],
) -> None:
    try:
        rows = conn.execute(
            "SELECT learned, completed, decisions FROM summaries "
            "WHERE project = ? ORDER BY created_at DESC LIMIT 20",
            (project_name,),
        ).fetchall()
    except sqlite3.OperationalError:
        return

    for row in rows:
        for col in ("learned", "completed", "decisions"):
            text = row[col]
            if text:
                _extract_tools_from_text(text, result, seen)


def _scan_observations(
    conn: sqlite3.Connection, project_name: str,
    result: ScanResult, seen: set[str],
) -> None:
    try:
        rows = conn.execute(
            "SELECT tool_input_summary FROM observations WHERE project = ? "
            "AND tool_input_summary IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 30",
            (project_name,),
        ).fetchall()
    except sqlite3.OperationalError:
        return

    for row in rows:
        _extract_tools_from_text(row["tool_input_summary"], result, seen)


def get_enrichment_context(concept_name: str) -> str | None:
    if not EAGLE_MEM_DB.exists():
        return None
    try:
        conn = sqlite3.connect(str(EAGLE_MEM_DB), timeout=3)
    except sqlite3.Error:
        return None

    snippets: list[str] = []
    queries = [
        ("summaries", "learned"),
        ("summaries", "completed"),
        ("summaries", "decisions"),
        ("claude_memories", "content"),
    ]
    escaped = (
        concept_name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    try:
        for table, col in queries:
            try:
                rows = conn.execute(
                    f"SELECT {col} FROM {table} WHERE {col} LIKE ? ESCAPE '\\' "  # noqa: S608
                    "ORDER BY rowid DESC LIMIT 5",
                    (f"%{escaped}%",),
                ).fetchall()
                for row in rows:
                    if row[0]:
                        snippets.append(row[0])
            except sqlite3.OperationalError:
                continue
    finally:
        conn.close()

    if not snippets:
        return None
    return "\n---\n".join(snippets)[:3000]


_CLI_TOOLS = {
    "railway": "devtool", "gh": "devtool", "eagle-mem": "devtool",
    "docker": "devtool", "kubectl": "devtool", "vercel": "devtool",
    "fly": "devtool", "terraform": "devtool", "ansible": "devtool",
    "claude": "devtool", "cursor": "devtool", "copilot": "devtool",
}


def scan_cli_tools(
    conn: sqlite3.Connection, project_name: str,
    result: ScanResult, seen: set[str],
) -> None:
    try:
        rows = conn.execute(
            "SELECT tool_input_summary FROM observations "
            "WHERE project = ? AND tool_name = 'Bash' "
            "AND tool_input_summary IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 200",
            (project_name,),
        ).fetchall()
    except sqlite3.OperationalError:
        return
    for row in rows:
        text = (row["tool_input_summary"] or "").lower()
        for tool, cat in _CLI_TOOLS.items():
            if tool not in seen and re.search(rf"\b{re.escape(tool)}\b", text):
                result.concepts.append(ScannedConcept(
                    name=tool, source="eagle_mem", category_hint=cat,
                ))
                seen.add(tool)


_SKILL_RE = re.compile(r"\b(eagle-[\w-]+|superpowers:[\w-]+)", re.IGNORECASE)
_CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"


def _scan_skill_usage(
    conn: sqlite3.Connection, project_name: str,
    result: ScanResult, seen: set[str],
) -> None:
    texts: list[str] = []
    try:
        rows = conn.execute(
            "SELECT tool_input_summary FROM observations "
            "WHERE project = ? AND tool_input_summary IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 300",
            (project_name,),
        ).fetchall()
        texts.extend(r["tool_input_summary"] for r in rows)
    except sqlite3.OperationalError:
        pass
    for mem_dir in _CLAUDE_PROJECTS.glob(f"*{project_name}*/memory"):
        for f in mem_dir.glob("*.md"):
            if f.name != "MEMORY.md":
                with contextlib.suppress(OSError):
                    texts.append(f.read_text(errors="ignore")[:1000])
    for text in texts:
        for match in _SKILL_RE.finditer(text):
            name = match.group(1).lower().rstrip("-")
            if name in seen or name == "eagle-mem":
                continue
            result.concepts.append(ScannedConcept(
                name=name, source="eagle_mem", category_hint="devtool",
            ))
            seen.add(name)


def _extract_tools_from_text(
    text: str, result: ScanResult, seen: set[str],
) -> None:
    patterns = [
        r"`(npm|pip|brew|cargo)\s+install\s+(-[gD]\s+)?(\S+)`",
        r"installed\s+(\S+)",
        r"using\s+(\S+)\s+(?:for|to|as)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            name = match.group(match.lastindex)
            name = name.strip("`'\".,;:")
            if not name or len(name) > 40 or name.lower() in seen:
                continue
            if name.startswith("-") or "/" in name:
                continue
            result.concepts.append(ScannedConcept(
                name=name, source="eagle_mem", category_hint="devtool",
            ))
            seen.add(name.lower())
