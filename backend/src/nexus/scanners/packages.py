from __future__ import annotations

import json
import tomllib
from pathlib import Path

from nexus.scanners import ScannedConcept, ScannedRelationship, ScanResult

_FRAMEWORKS = {
    "react", "react-dom", "vue", "svelte", "angular", "next", "nuxt",
    "solid-js", "preact", "express", "fastapi", "flask", "django",
    "fastify", "hono", "nest", "koa", "sveltekit", "tailwindcss", "bootstrap",
}
_DEVTOOLS = {
    "eslint", "prettier", "biome", "vitest", "jest", "playwright", "cypress",
    "mocha", "pytest", "ruff", "mypy", "black", "webpack", "vite", "esbuild",
    "rollup", "turbopack", "parcel", "docker", "storybook", "husky",
}
_LANGUAGES = {"typescript", "python", "rust"}
_KNOWN_CATEGORIES = {
    **{n: "framework" for n in _FRAMEWORKS},
    **{n: "devtool" for n in _DEVTOOLS},
    **{n: "language" for n in _LANGUAGES},
}

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
        cat = _KNOWN_CATEGORIES.get(name.lower(), "library")
        result.concepts.append(ScannedConcept(
            name=name, source="package_scan", category_hint=cat,
            setup_command=f"npm install {name}",
        ))
        seen.add(name.lower())

    for name in dev_deps:
        if _should_skip(name) or name.lower() in seen:
            continue
        cat = _KNOWN_CATEGORIES.get(name.lower(), "devtool")
        result.concepts.append(ScannedConcept(
            name=name, source="package_scan", category_hint=cat,
            is_dev_dep=True, setup_command=f"npm install -D {name}",
        ))
        seen.add(name.lower())

    _infer_npm_relationships(result, deps, dev_deps)


_TEST_TOOLS = {"test", "jest", "vitest", "mocha", "cypress", "playwright"}
_BUILD_TOOLS = {"webpack", "vite", "esbuild", "rollup", "turbopack", "parcel", "tsup"}
_LINT_TOOLS = {"eslint", "prettier", "biome", "oxlint", "stylelint"}
_CONFIG_PAIRS = {
    "postcss": "tailwindcss", "tailwindcss": "postcss",
    "typescript": "ts-node", "ts-node": "typescript",
}


def _infer_npm_relationships(result: ScanResult, deps: dict, dev_deps: dict) -> None:
    all_deps = {**deps, **dev_deps}
    all_lower = {n.lower() for n in all_deps}
    seen_pairs: set[tuple[str, str]] = set()

    def _add(src: str, tgt: str, rel: str, reason: str | None = None) -> None:
        pair = (src.lower(), tgt.lower())
        if pair not in seen_pairs and pair[0] != pair[1]:
            seen_pairs.add(pair)
            result.relationships.append(ScannedRelationship(
                source_name=src, target_name=tgt,
                relationship=rel, reason=reason,
            ))

    for name in all_deps:
        lower = name.lower()
        # Sub-package: @tailwindcss/postcss part_of tailwindcss
        if "/" in lower:
            scope = lower.split("/")[0].lstrip("@")
            if scope in all_lower:
                parent = next(n for n in all_deps if n.lower() == scope)
                _add(name, parent, "part_of", "sub-package")
        for tool in (*_LINT_TOOLS, *_TEST_TOOLS, *_BUILD_TOOLS):
            is_plugin = lower.startswith(f"{tool}-") or lower.startswith(f"@{tool}/")
            if is_plugin and tool in all_lower:
                parent = next(n for n in all_deps if n.lower() == tool)
                _add(name, parent, "configured_by", "plugin")

    for name in all_deps:
        partner = _CONFIG_PAIRS.get(name.lower())
        if partner and partner in all_lower:
            target = next(n for n in all_deps if n.lower() == partner)
            _add(name, target, "configured_by", "config pair")


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
        spec = raw.split(";")[0]  # strip env markers
        name = (
            spec.split(">=")[0].split("~=")[0].split("!=")[0]
            .split("==")[0].split("<")[0].split("[")[0].strip()
        )
        if not name or name.startswith("#") or " " in name or "=" in name:
            continue
        lower = name.lower()
        if lower in seen or lower in workspace_names:
            continue
        seen.add(lower)
        cat = _KNOWN_CATEGORIES.get(lower, "library")
        result.concepts.append(ScannedConcept(
            name=name, source="package_scan", category_hint=cat,
            setup_command=f"uv add {name}",
        ))


def _parse_requirements(path: Path, result: ScanResult, seen: set[str]) -> None:
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return
    for raw_line in lines:
        raw_line = raw_line.strip()
        if not raw_line or raw_line.startswith(("#", "-")):
            continue
        spec = raw_line.split(";")[0]
        name = spec.split(">=")[0].split("~=")[0].split("!=")[0]
        name = name.split("==")[0].split("<")[0].split("[")[0].strip()
        if not name:
            continue
        lower = name.lower()
        if lower in seen:
            continue
        seen.add(lower)
        cat = _KNOWN_CATEGORIES.get(lower, "library")
        result.concepts.append(ScannedConcept(
            name=name, source="package_scan", category_hint=cat,
            setup_command=f"pip install {name}",
        ))
