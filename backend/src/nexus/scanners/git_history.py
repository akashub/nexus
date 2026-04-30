from __future__ import annotations

import re
import subprocess
from pathlib import Path

from nexus.scanners import ScannedRelationship, ScanResult


def scan_git_history(project_path: Path) -> ScanResult:
    result = ScanResult()
    if not (project_path / ".git").exists():
        return result

    log_output = _run_git(project_path, ["log", "--oneline", "-50"])
    if not log_output:
        return result

    _infer_relationships_from_commits(log_output, result)
    return result


def _run_git(cwd: Path, args: list[str]) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(cwd),
            capture_output=True, text=True, timeout=10,
        )
        return proc.stdout.strip() if proc.returncode == 0 else None
    except (subprocess.TimeoutExpired, OSError):
        return None


_INSTALL_PATTERN = re.compile(
    r"(?:npm install|pip install|brew install|cargo add|uv add)\s+(\S+)",
    re.IGNORECASE,
)

_SKIP_WORDS = frozenset({
    "the", "a", "an", "to", "for", "and", "with", "from", "in", "on",
    "new", "add", "fix", "update", "remove", "refactor", "test",
})


def _infer_relationships_from_commits(
    log_output: str, result: ScanResult,
) -> None:
    tools_added: list[str] = []
    for line in log_output.splitlines():
        msg = line.split(" ", 1)[1] if " " in line else line
        for match in _INSTALL_PATTERN.finditer(msg):
            tool = match.group(1).strip(".,;:'\"()")
            if tool and 2 < len(tool) < 30 and tool.lower() not in _SKIP_WORDS:
                tools_added.append(tool)

    for i, a in enumerate(tools_added):
        for b in tools_added[i + 1: i + 3]:
            if a.lower() != b.lower():
                result.relationships.append(ScannedRelationship(
                    source_name=a, target_name=b,
                    relationship="related_to",
                    reason="installed in nearby commits",
                ))
