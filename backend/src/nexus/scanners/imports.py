from __future__ import annotations

import ast
import re
from pathlib import Path

from nexus.scanners import ScannedRelationship, ScanResult

_ENTRY_POINTS = [
    "main.py", "app.py", "server.py", "cli.py", "index.py",
    "manage.py", "__main__.py",
]
_ENTRY_GLOBS = ["src/*/server.py", "src/*/cli.py", "src/*/app.py"]
_TS_ENTRY_POINTS = ["index.ts", "index.tsx", "main.ts", "main.tsx", "app.ts", "app.tsx"]

_SKIP_DIRS = frozenset({
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".tox", ".mypy_cache", ".ruff_cache", "dist", "build",
    ".next", ".nuxt", "coverage", "egg-info",
})


def scan_imports(
    project_path: Path, *, depth: int = 0, known_concepts: set[str] | None = None,
) -> ScanResult:
    if depth < 1 or not known_concepts:
        return ScanResult()

    result = ScanResult()
    lower_map = {n.lower(): n for n in known_concepts}

    files = _find_entry_points(project_path) if depth == 1 else _find_all_source_files(project_path)

    for f in files:
        if f.suffix == ".py":
            raw_imports = _extract_python_imports(f)
        elif f.suffix in (".ts", ".tsx", ".js", ".jsx"):
            raw_imports = _extract_ts_imports(f)
        else:
            continue

        matched = []
        for module in raw_imports:
            match = lower_map.get(module.lower())
            if match:
                matched.append(match)

        # Cap to avoid O(n^2) explosion in files with many matched imports
        for i, src in enumerate(matched[:30]):
            for tgt in matched[i + 1:30]:
                result.relationships.append(ScannedRelationship(
                    source_name=src, target_name=tgt,
                    relationship="uses",
                    reason=f"co-imported in {f.name}",
                ))

    _deduplicate(result)
    return result


def _find_entry_points(root: Path) -> list[Path]:
    files: list[Path] = []
    for name in _ENTRY_POINTS:
        p = root / name
        if p.exists():
            files.append(p)
    for pattern in _ENTRY_GLOBS:
        files.extend(root.glob(pattern))
    for name in _TS_ENTRY_POINTS:
        p = root / "src" / name
        if p.exists():
            files.append(p)
    return files


def _find_all_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*"):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        if p.suffix in (".py", ".ts", ".tsx", ".js", ".jsx"):
            files.append(p)
    return files[:500]


def _extract_python_imports(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except (SyntaxError, OSError):
        return []
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                modules.append(top)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            modules.append(top)
    return list(set(modules))


_TS_IMPORT_RE = re.compile(
    r"""(?:import|require)\s*\(?\s*['"]([^'"]+)['"]""",
)


def _extract_ts_imports(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except OSError:
        return []
    modules: list[str] = []
    for match in _TS_IMPORT_RE.finditer(text):
        raw = match.group(1)
        if raw.startswith(".") or raw.startswith("/"):
            continue
        if raw.startswith("@"):
            modules.append(raw.split("/")[0] + "/" + raw.split("/")[1] if "/" in raw else raw)
        else:
            modules.append(raw.split("/")[0])
    return list(set(modules))


def _deduplicate(result: ScanResult) -> None:
    seen: set[tuple[str, str, str]] = set()
    unique: list[ScannedRelationship] = []
    for r in result.relationships:
        key = (r.source_name.lower(), r.target_name.lower(), r.relationship)
        if key not in seen:
            seen.add(key)
            unique.append(r)
    result.relationships = unique
