from __future__ import annotations

import json
import tomllib
from pathlib import Path

from nexus.scanners import ScannedConcept, ScannedRelationship, ScanResult

_SKIP_PACKAGES = frozenset(
    {"typescript", "types", "@types", "ts-node", "tslib", "eslint-config-", "prettier", "@eslint"},
)


def _should_skip(name: str) -> bool:
    lower = name.lower()
    return any(lower.startswith(s) for s in _SKIP_PACKAGES) or lower.startswith("@types/")


def scan_npm(project_path: Path) -> ScanResult:
    candidates = [project_path / "package.json"]
    for child in project_path.iterdir():
        if child.is_dir() and not child.name.startswith((".", "node_modules")):
            candidate = child / "package.json"
            if candidate.exists():
                candidates.append(candidate)

    result = ScanResult()
    for pkg_file in candidates:
        if pkg_file.exists():
            _scan_single_npm(pkg_file, result)
    return result


def _scan_single_npm(pkg_file: Path, result: ScanResult) -> None:
    try:
        pkg = json.loads(pkg_file.read_text())
    except (json.JSONDecodeError, OSError):
        return

    if pkg.get("description") and not result.project_description:
        result.project_description = pkg.get("description")
    deps = pkg.get("dependencies", {})
    dev_deps = pkg.get("devDependencies", {})
    seen = {c.name.lower() for c in result.concepts}

    for name in deps:
        if _should_skip(name) or name.lower() in seen:
            continue
        result.concepts.append(ScannedConcept(
            name=name, source="package_scan", category_hint="framework",
            setup_command=f"npm install {name}",
        ))
        seen.add(name.lower())

    for name in dev_deps:
        if _should_skip(name) or name.lower() in seen:
            continue
        result.concepts.append(ScannedConcept(
            name=name, source="package_scan", category_hint="devtool",
            is_dev_dep=True, setup_command=f"npm install -D {name}",
        ))
        seen.add(name.lower())

    _infer_npm_relationships(result, deps, dev_deps)


_TEST_TOOLS = {"test", "jest", "vitest", "mocha", "cypress", "playwright"}
_BUILD_TOOLS = {"webpack", "vite", "esbuild", "rollup", "turbopack", "parcel", "tsup"}
_LINT_TOOLS = {"eslint", "prettier", "biome", "oxlint", "stylelint"}
_FRAMEWORKS = ["react", "vue", "svelte", "angular", "next", "nuxt", "solid", "preact"]
_CONFIG_PAIRS = {
    "postcss": "tailwindcss", "tailwindcss": "postcss",
    "typescript": "ts-node", "ts-node": "typescript",
}


def _find_main_framework(deps: dict) -> str | None:
    for fw in _FRAMEWORKS:
        match = next((n for n in deps if n.lower() == fw or n.lower().endswith(f"/{fw}")), None)
        if match:
            return match
    return next(iter(deps), None)


def _infer_npm_relationships(result: ScanResult, deps: dict, dev_deps: dict) -> None:
    all_deps = {**deps, **dev_deps}
    main_fw = _find_main_framework(deps)

    for name in dev_deps:
        lower = name.lower()
        if any(t in lower for t in _TEST_TOOLS) and main_fw:
            result.relationships.append(ScannedRelationship(
                source_name=name, target_name=main_fw,
                relationship="tested_with",
            ))
        elif any(t in lower for t in _BUILD_TOOLS) and main_fw:
            result.relationships.append(ScannedRelationship(
                source_name=name, target_name=main_fw,
                relationship="builds_into",
            ))
        elif any(t in lower for t in _LINT_TOOLS) and main_fw:
            result.relationships.append(ScannedRelationship(
                source_name=name, target_name=main_fw,
                relationship="configured_by",
            ))

    for name in all_deps:
        partner = _CONFIG_PAIRS.get(name.lower())
        if partner and any(d.lower() == partner for d in all_deps):
            result.relationships.append(ScannedRelationship(
                source_name=name, target_name=partner,
                relationship="configured_by",
            ))


_SKIP_DIRS = frozenset(
    {".git", ".venv", "venv", "__pycache__", "node_modules", ".tox", ".mypy_cache"},
)


def scan_python(project_path: Path) -> ScanResult:
    result = ScanResult()
    workspace_names = _find_workspace_names(project_path)
    seen: set[str] = set()
    for pyproject in project_path.rglob("pyproject.toml"):
        if any(p in _SKIP_DIRS for p in pyproject.parts):
            continue
        _parse_pyproject(pyproject, result, workspace_names, seen)
    for req_file in project_path.rglob("requirements.txt"):
        if any(p in _SKIP_DIRS for p in req_file.parts):
            continue
        _parse_requirements(req_file, result, seen)
    return result


def _find_workspace_names(root: Path) -> set[str]:
    names: set[str] = set()
    for pp in root.rglob("pyproject.toml"):
        if any(p in _SKIP_DIRS for p in pp.parts):
            continue
        try:
            data = tomllib.loads(pp.read_text())
            val = data.get("project", {}).get("name", "")
            if val:
                names.add(val.lower())
        except (OSError, tomllib.TOMLDecodeError):
            pass
    return names


def _parse_pyproject(
    path: Path, result: ScanResult, workspace_names: set[str], seen: set[str],
) -> None:
    try:
        data = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return
    deps = data.get("project", {}).get("dependencies", [])
    for raw in deps:
        name = raw.split(">=")[0].split("==")[0].split("<")[0].split("[")[0].strip()
        if not name or name.startswith("#") or " " in name or "=" in name:
            continue
        lower = name.lower()
        if lower in seen or lower in workspace_names:
            continue
        seen.add(lower)
        result.concepts.append(ScannedConcept(
            name=name, source="package_scan", category_hint="framework",
            setup_command=f"uv add {name}",
        ))


def _parse_requirements(path: Path, result: ScanResult, seen: set[str]) -> None:
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        name = line.split(">=")[0].split("==")[0].split("<")[0].split("[")[0].strip()
        if not name:
            continue
        lower = name.lower()
        if lower in seen:
            continue
        seen.add(lower)
        result.concepts.append(ScannedConcept(
            name=name, source="package_scan", category_hint="framework",
            setup_command=f"pip install {name}",
        ))
