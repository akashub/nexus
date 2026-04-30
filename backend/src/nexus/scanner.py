from __future__ import annotations

import logging
from pathlib import Path

import click

from nexus.scanners import ScanResult
from nexus.scanners.claude_md import scan_claude_md
from nexus.scanners.eagle_mem import scan_eagle_mem
from nexus.scanners.git_history import scan_git_history
from nexus.scanners.mcp import scan_mcp
from nexus.scanners.packages import scan_npm, scan_python

log = logging.getLogger(__name__)


def scan_project(project_path: Path, *, verbose: bool = False) -> ScanResult:
    path = project_path.resolve()
    if not path.is_dir():
        raise click.ClickException(f"Not a directory: {path}")

    result = ScanResult()

    scanners = [
        ("packages (npm)", lambda: scan_npm(path)),
        ("packages (python)", lambda: scan_python(path)),
        ("CLAUDE.md", lambda: scan_claude_md(path)),
        ("MCP configs", lambda: scan_mcp(path)),
        ("Eagle Mem", lambda: scan_eagle_mem(path)),
        ("git history", lambda: scan_git_history(path)),
    ]

    for name, scanner_fn in scanners:
        try:
            partial = scanner_fn()
            if verbose and (partial.concepts or partial.relationships):
                click.echo(f"  {name}: {len(partial.concepts)} concepts, "
                           f"{len(partial.relationships)} relationships")
            result.merge(partial)
        except Exception:
            log.exception("Scanner %s failed", name)
            if verbose:
                click.echo(f"  {name}: scanner failed, skipping")

    return result
