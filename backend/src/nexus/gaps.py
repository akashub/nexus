"""Gap detection — find missing companion tools for a project."""

from __future__ import annotations

import re
import sqlite3

from nexus.db_concepts import list_concepts

COMPANION_PATTERNS = {
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
    "ci_cd": {
        "signals": ["react", "fastapi", "express", "django", "next"],
        "companions": ["github-actions", "pre-commit", "husky", "lint-staged"],
        "reason": "Production apps need CI/CD pipelines",
        "label": "CI/CD pipeline",
    },
    "monitoring": {
        "signals": ["fastapi", "express", "django", "flask", "next"],
        "companions": ["sentry", "pino", "structlog", "winston", "datadog"],
        "reason": "Server apps need observability and error tracking",
        "label": "monitoring/logging",
    },
    "state_management": {
        "signals": ["react", "vue", "svelte"],
        "companions": ["zustand", "jotai", "redux", "pinia", "tanstack-query"],
        "reason": "Frontend apps with complexity need state management",
        "label": "state management",
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
    """Normalize concept name: lowercase, strip @scope/ prefix."""
    n = name.lower().strip()
    n = re.sub(r"^@[^/]+/", "", n)
    return n


def detect_gaps(conn: sqlite3.Connection, project_id: str | None = None) -> list[dict]:
    """Detect missing companion tools for a project's stack."""
    concepts = list_concepts(conn, project_id=project_id, limit=10000)
    normalized = {_normalize(c.name) for c in concepts}

    gaps = []
    for category, pattern in COMPANION_PATTERNS.items():
        matched_signals = [s for s in pattern["signals"] if s in normalized]
        if not matched_signals:
            continue
        has_companion = any(
            any(c == n or n.startswith(c + "-") or n.endswith("-" + c) for n in normalized)
            for c in pattern["companions"]
        )
        if has_companion:
            continue
        gaps.append({
            "category": category,
            "reason": pattern["reason"],
            "have": matched_signals,
            "missing_type": pattern["label"],
            "suggestions": pattern["companions"],
        })
    return gaps


def format_gaps_report(project_name: str | None, gaps: list[dict]) -> str:
    """Format gap results as human-readable text."""
    if not gaps:
        return "No gaps detected -- your project looks well-rounded!"

    header = f"Gaps detected for {project_name}:" if project_name else "Gaps detected:"
    lines = [header, ""]
    for gap in gaps:
        title = gap["category"].replace("_", " ").title()
        have = ", ".join(gap["have"])
        suggestions = ", ".join(gap["suggestions"])
        lines.append(f"  {title}")
        lines.append(f"    You have: {have}")
        lines.append(f"    Missing:  {gap['missing_type']} ({suggestions})")
        lines.append(f"    Why:      {gap['reason']}")
        lines.append("")

    count = len(gaps)
    noun = "gap" if count == 1 else "gaps"
    lines.append(f"{count} {noun} detected. Run `nexus add <name>` to fill them.")
    return "\n".join(lines)
