from __future__ import annotations

import json
from pathlib import Path

from nexus.scanners import ScannedConcept, ScannedRelationship, ScanResult

_SKIP_PACKAGES = frozenset({
    "typescript", "types", "@types", "ts-node", "tslib",
    "eslint-config-", "prettier", "@eslint",
})


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
        for name in deps:
            if name.lower() == fw or name.lower().endswith(f"/{fw}"):
                return name
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


def scan_python(project_path: Path) -> ScanResult:
    result = ScanResult()
    search_dirs = [project_path]
    for child in project_path.iterdir():
        if child.is_dir() and not child.name.startswith("."):
            search_dirs.append(child)
    for d in search_dirs:
        pyproject = d / "pyproject.toml"
        if pyproject.exists():
            _parse_pyproject(pyproject, result)
        req_file = d / "requirements.txt"
        if req_file.exists():
            _parse_requirements(req_file, result)
    return result


def _parse_pyproject(path: Path, result: ScanResult) -> None:
    try:
        text = path.read_text()
    except OSError:
        return
    # Minimal TOML parsing for dependencies — avoids adding toml dep
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        is_deps = stripped == "dependencies = [" or stripped.startswith("dependencies")
        if is_deps and "[" in stripped:
            in_deps = True
            continue
        if in_deps:
            if stripped == "]":
                in_deps = False
                continue
            raw = stripped.strip('"').strip("',")
            name = raw.split(">=")[0].split("==")[0].split("<")[0].strip()
            if name and not name.startswith("#"):
                result.concepts.append(ScannedConcept(
                    name=name, source="package_scan", category_hint="framework",
                    setup_command=f"uv add {name}",
                ))


def _parse_requirements(path: Path, result: ScanResult) -> None:
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        name = line.split(">=")[0].split("==")[0].split("<")[0].split("[")[0].strip()
        if name:
            result.concepts.append(ScannedConcept(
                name=name, source="package_scan", category_hint="framework",
                setup_command=f"pip install {name}",
            ))
