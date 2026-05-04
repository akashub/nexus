from __future__ import annotations

import re
from pathlib import Path

from nexus.scanners import ScannedConcept, ScanResult


def scan_claude_md(project_path: Path) -> ScanResult:
    result = ScanResult()
    for filename in ("CLAUDE.md", "AGENTS.md"):
        path = project_path / filename
        if path.exists():
            _parse_file(path, result)
    return result


def _parse_file(path: Path, result: ScanResult) -> None:
    try:
        text = path.read_text()
    except OSError:
        return

    seen = {c.name.lower() for c in result.concepts}

    stack_section = _extract_section(text, "Stack")
    if stack_section:
        _extract_tools_from_section(stack_section, result, seen)

    desc_section = _extract_section(text, "")
    if desc_section and not result.project_description:
        first_para = desc_section.split("\n\n")[0].strip()
        if 10 < len(first_para) < 500:
            result.project_description = first_para


def _extract_section(text: str, heading: str) -> str | None:
    if not heading:
        lines = text.split("\n")
        content = []
        for line in lines:
            if line.startswith("# "):
                if content:
                    break
                continue
            content.append(line)
        return "\n".join(content).strip() or None

    pattern = rf"^##\s+{re.escape(heading)}\b.*$"
    match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
    if not match:
        return None
    start = match.end()
    next_heading = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end].strip()


_TOOL_PATTERN = re.compile(
    r"\*\*([^*]+)\*\*[:\s]*([^.\n]+)", re.IGNORECASE,
)

_SKIP_GENERIC = {
    "monorepo", "backend", "frontend", "database", "api", "server",
    "client", "desktop", "mobile", "web", "docs", "tests", "scripts",
    "styling", "hard rules", "development workflow", "directory layout",
    "ai", "docs fetch", "graph viz", "package management",
    "framework", "auth", "repo", "real-time", "offline", "offline/pwa",
    "deployment", "hosting", "infra", "infrastructure", "storage",
    "cache", "queue", "messaging", "analytics", "security", "logging",
    "monitoring", "ci/cd", "build system",
}


def _extract_tools_from_section(
    text: str, result: ScanResult, seen: set[str],
) -> None:
    for match in _TOOL_PATTERN.finditer(text):
        name = match.group(1).strip()
        if name.lower() in seen or name.lower() in _SKIP_GENERIC or len(name) > 50:
            continue
        words = name.split()
        if len(words) > 3:
            continue
        category = _guess_category(name, match.group(2))
        result.concepts.append(ScannedConcept(
            name=name, source="claude_md", category_hint=category,
            context=match.group(2).strip(),
        ))
        seen.add(name.lower())


def _guess_category(name: str, desc: str) -> str:
    lower = (name + " " + desc).lower()
    if any(w in lower for w in ("test", "lint", "format", "ci", "build")):
        return "devtool"
    if any(w in lower for w in ("framework", "react", "vue", "django", "flask", "fastapi")):
        return "framework"
    if any(w in lower for w in ("database", "db", "sql", "redis", "mongo")):
        return "concept"
    if any(w in lower for w in ("pattern", "architecture", "design")):
        return "pattern"
    if any(w in lower for w in ("python", "rust", "go", "java", "typescript")):
        return "language"
    return "devtool"
