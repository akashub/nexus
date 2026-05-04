"""Gap detection — find missing companion tools for a project."""

from __future__ import annotations

import json
import logging
import re
import sqlite3

from nexus.db_concepts import list_concepts

log = logging.getLogger(__name__)

_SYSTEM = (
    "You are a senior developer reviewing a project's tech stack. "
    "Identify missing tools or practices that would improve the project."
)

_PROMPT = """A project has these tools/concepts in its knowledge graph:
{concepts}

Analyze this stack and identify 2-5 gaps — categories of tools that are missing
and would benefit the project. Only flag genuine gaps, not nice-to-haves.

For each gap, suggest 2-4 specific tools that could fill it.
Respond in EXACTLY this JSON format, nothing else:
[{{"category": "short category name",
   "reason": "why this project needs this",
   "have": ["existing tools that signal this need"],
   "missing_type": "what kind of tool is missing",
   "suggestions": ["tool1", "tool2"]}}]

If the stack looks complete, return an empty array: []"""


def detect_gaps(conn: sqlite3.Connection, project_id: str | None = None) -> list[dict]:
    """Detect missing tools using AI, fall back to pattern matching."""
    concepts = list_concepts(conn, project_id=project_id, limit=10000)
    if not concepts:
        return []

    result = _detect_gaps_ai(concepts)
    if result is not None:
        return result
    return _detect_gaps_patterns(concepts)


def _detect_gaps_ai(concepts: list) -> list[dict] | None:
    from nexus.ai import is_available, smart_generate
    if not is_available():
        return None

    concept_lines = []
    for c in concepts:
        parts = [c.name]
        if c.category:
            parts.append(f"[{c.category}]")
        if c.summary:
            parts.append(f"— {c.summary}")
        concept_lines.append(" ".join(parts))

    prompt = _PROMPT.format(concepts="\n".join(concept_lines))
    try:
        raw = smart_generate(prompt, system=_SYSTEM)
        start, end = raw.find("["), raw.rfind("]") + 1
        if start < 0 or end <= start:
            return None
        data = json.loads(raw[start:end])
        if not isinstance(data, list):
            return None
        gaps = []
        for item in data:
            if not isinstance(item, dict) or "category" not in item:
                continue
            gaps.append({
                "category": str(item.get("category", "")),
                "reason": str(item.get("reason", "")),
                "have": [str(h) for h in item.get("have", [])],
                "missing_type": str(item.get("missing_type", "")),
                "suggestions": [str(s) for s in item.get("suggestions", [])],
            })
        return gaps
    except Exception:
        log.debug("AI gap detection failed, falling back to patterns", exc_info=True)
        return None


_PATTERNS = {
    "testing": {
        "signals": ["react", "vue", "svelte", "angular", "fastapi", "express", "django", "flask"],
        "companions": ["vitest", "jest", "pytest", "playwright", "cypress", "mocha"],
        "reason": "Projects with frameworks typically need testing tools",
        "label": "test runner",
    },
    "linting": {
        "signals": ["react", "typescript", "vue", "angular"],
        "companions": ["eslint", "prettier", "biome", "ruff", "oxlint"],
        "reason": "Frontend projects benefit from linting and formatting",
        "label": "linter/formatter",
    },
    "database": {
        "signals": ["fastapi", "express", "django", "flask", "next"],
        "companions": ["prisma", "drizzle", "sqlalchemy", "typeorm", "sequelize", "knex"],
        "reason": "Server apps typically need a database layer",
        "label": "database/ORM",
    },
    "styling": {
        "signals": ["react", "vue", "svelte", "angular", "next"],
        "companions": ["tailwindcss", "styled-components", "css-modules", "sass", "postcss"],
        "reason": "Frontend projects need a styling solution",
        "label": "styling solution",
    },
}


def _normalize(name: str) -> str:
    n = name.lower().strip()
    return re.sub(r"^@[^/]+/", "", n)


def _detect_gaps_patterns(concepts: list) -> list[dict]:
    normalized = {_normalize(c.name) for c in concepts}
    gaps = []
    for category, p in _PATTERNS.items():
        matched = [s for s in p["signals"] if s in normalized]
        if not matched:
            continue
        has = any(
            any(c == n or n.startswith(c + "-") or n.endswith("-" + c) for n in normalized)
            for c in p["companions"]
        )
        if has:
            continue
        gaps.append({
            "category": category, "reason": p["reason"],
            "have": matched, "missing_type": p["label"],
            "suggestions": p["companions"],
        })
    return gaps


def format_gaps_report(project_name: str | None, gaps: list[dict]) -> str:
    if not gaps:
        return "No gaps detected -- your project looks well-rounded!"
    header = f"Gaps detected for {project_name}:" if project_name else "Gaps detected:"
    lines = [header, ""]
    for gap in gaps:
        title = gap["category"].replace("_", " ").title()
        lines.append(f"  {title}")
        if gap.get("have"):
            lines.append(f"    You have: {', '.join(gap['have'])}")
        lines.append(f"    Missing:  {gap['missing_type']} ({', '.join(gap['suggestions'])})")
        lines.append(f"    Why:      {gap['reason']}")
        lines.append("")
    count = len(gaps)
    noun = "gap" if count == 1 else "gaps"
    lines.append(f"{count} {noun} detected. Run `nexus add <name>` to fill them.")
    return "\n".join(lines)
