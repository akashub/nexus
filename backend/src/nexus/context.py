from __future__ import annotations

import sqlite3
from pathlib import Path

EAGLE_DB = Path.home() / ".eagle-mem" / "memory.db"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"


def _eagle_conn() -> sqlite3.Connection | None:
    if not EAGLE_DB.exists():
        return None
    conn = sqlite3.connect(str(EAGLE_DB))
    conn.row_factory = sqlite3.Row
    return conn


def get_eagle_overview(project_name: str) -> str | None:
    conn = _eagle_conn()
    if not conn:
        return None
    try:
        row = conn.execute(
            "SELECT content FROM overviews WHERE project = ?",
            (project_name,),
        ).fetchone()
        return row["content"] if row else None
    finally:
        conn.close()


def search_session_context(
    project_name: str, query: str, limit: int = 5,
) -> list[str]:
    conn = _eagle_conn()
    if not conn:
        return []
    try:
        snippets: list[str] = []
        q = f"%{query}%"
        for col in ("learned", "completed", "decisions"):
            try:
                rows = conn.execute(
                    f"SELECT {col} FROM summaries "  # noqa: S608
                    "WHERE project = ? AND " + col + " LIKE ? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (project_name, q, limit),
                ).fetchall()
                for r in rows:
                    if r[col]:
                        snippets.append(r[col][:200])
            except sqlite3.OperationalError:
                continue
        return snippets[:limit]
    finally:
        conn.close()


def search_eagle_code(project_name: str, query: str, limit: int = 5) -> list[str]:
    conn = _eagle_conn()
    if not conn:
        return []
    try:
        rows = conn.execute(
            "SELECT content, file_path FROM code_chunks_fts "
            "WHERE code_chunks_fts MATCH ? LIMIT ?",
            (f'"{query}"', limit),
        ).fetchall()
        return [f"{r['file_path']}:\n{r['content'][:300]}" for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


_INSTALL_PATTERNS = [
    "pip install%", "uv add%", "uv pip install%",
    "npm install%", "pnpm add%", "yarn add%",
    "brew install%", "cargo install%", "apt install%",
]


def get_install_commands(project_name: str, concept_name: str) -> list[str]:
    conn = _eagle_conn()
    if not conn:
        return []
    try:
        results: list[str] = []
        lower_name = concept_name.lower()
        for pattern in _INSTALL_PATTERNS:
            rows = conn.execute(
                "SELECT tool_input_summary FROM observations "
                "WHERE project = ? AND tool_name = 'Bash' "
                "AND tool_input_summary LIKE ? "
                "ORDER BY created_at DESC LIMIT 3",
                (project_name, f"Bash: {pattern}"),
            ).fetchall()
            for r in rows:
                s = r["tool_input_summary"] or ""
                if lower_name in s.lower():
                    cmd = s.replace("Bash: ", "", 1).strip()
                    results.append(cmd)
        return results[:3]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def _claude_memory_dir(project_path: str) -> Path | None:
    encoded = project_path.replace("/", "-")
    candidate = CLAUDE_PROJECTS / encoded / "memory"
    if candidate.exists():
        return candidate
    for d in CLAUDE_PROJECTS.iterdir():
        if d.is_dir() and project_path.split("/")[-1] in d.name:
            mem = d / "memory"
            if mem.exists():
                return mem
    return None


def get_claude_memories(project_path: str) -> list[dict]:
    mem_dir = _claude_memory_dir(project_path)
    if not mem_dir:
        return []
    memories = []
    for f in mem_dir.glob("*.md"):
        if f.name == "MEMORY.md":
            continue
        text = f.read_text(errors="ignore")
        name = f.stem
        mem_type = "project"
        for line in text.splitlines()[:8]:
            if line.startswith("type:"):
                mem_type = line.split(":", 1)[1].strip()
                break
        body = text
        if body.startswith("---"):
            end = body.find("---", 3)
            if end > 0:
                body = body[end + 3:].strip()
        memories.append({"name": name, "type": mem_type, "content": body[:500]})
    return memories


def get_concept_context(
    project_name: str, project_path: str, concept_name: str,
) -> str:
    parts: list[str] = []
    sessions = search_session_context(project_name, concept_name, limit=5)
    if sessions:
        parts.append("From sessions:\n" + "\n".join(sessions))
    memories = get_claude_memories(project_path)
    relevant = [m for m in memories if concept_name.lower() in m["content"].lower()]
    if relevant:
        parts.append("From Claude memories:\n" + "\n".join(
            m["content"][:200] for m in relevant[:3]
        ))
    installs = get_install_commands(project_name, concept_name)
    if installs:
        parts.append("Install history:\n" + "\n".join(installs[:3]))
    return "\n\n".join(parts) if parts else ""


_usage_cache: dict[str, str] = {}


def summarize_usage(concept_name: str, raw_context: str) -> str:
    if concept_name in _usage_cache:
        return _usage_cache[concept_name]
    from nexus.ai import generate, is_available
    if not is_available() or not raw_context:
        return ""
    prompt = (f"Summarize how '{concept_name}' is used in this project "
              f"from this session activity. 2-3 sentences.\n\n{raw_context[:800]}")
    try:
        result = generate(prompt, system="Summarize developer tool usage concisely.").strip()
        _usage_cache[concept_name] = result
        return result
    except Exception:
        return ""


_TOOL_NAMES = ("railway", "gh", "eagle-mem", "docker", "kubectl", "vercel")


def discover_tools_from_eagle(project_name: str) -> list[str]:
    conn = _eagle_conn()
    if not conn:
        return []
    try:
        like_clauses = " OR ".join(
            f"tool_input_summary LIKE '%{t}%'" for t in _TOOL_NAMES
        )
        rows = conn.execute(
            f"SELECT DISTINCT tool_input_summary FROM observations "
            f"WHERE project = ? AND tool_name = 'Bash' "
            f"AND ({like_clauses}) LIMIT 50",
            (project_name,),
        ).fetchall()
        tools: set[str] = set()
        for r in rows:
            s = (r["tool_input_summary"] or "").lower()
            tools.update(t for t in _TOOL_NAMES if t in s)
        return sorted(tools)
    finally:
        conn.close()
