from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from nexus.db import get_project, list_concepts
from nexus.db_concepts import get_edges
from nexus.scanners.packages import scan_npm, scan_python


@dataclass
class ExpertiseEntry:
    name: str
    level: str
    category: str | None = None
    signals: list[str] = field(default_factory=list)


@dataclass
class ExpertiseProfile:
    project_name: str
    total: int = 0
    known_well: list[ExpertiseEntry] = field(default_factory=list)
    seen: list[ExpertiseEntry] = field(default_factory=list)
    gaps: list[ExpertiseEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        def _entries(items: list[ExpertiseEntry]) -> list[dict]:
            return [{"name": e.name, "category": e.category, "signals": e.signals} for e in items]
        return {
            "project": self.project_name,
            "total": self.total,
            "known_well": _entries(self.known_well),
            "seen": _entries(self.seen),
            "gaps": _entries(self.gaps),
        }


def classify_expertise(conn: sqlite3.Connection, project_id: str) -> ExpertiseProfile:
    project = get_project(conn, project_id)
    if not project:
        return ExpertiseProfile(project_name="unknown")

    concepts = list_concepts(conn, project_id=project_id, limit=10000)
    profile = ExpertiseProfile(project_name=project.name)

    for c in concepts:
        signals = []
        if c.description:
            signals.append("desc")
        if c.embedding:
            signals.append("embedding")
        edges = get_edges(conn, c.id)
        if edges:
            signals.append(f"{len(edges)} edges")

        entry = ExpertiseEntry(name=c.name, level="", category=c.category, signals=signals)

        has_desc = c.description is not None
        has_embed = c.embedding is not None
        has_edges = len(edges) >= 1

        if has_desc and has_embed and has_edges:
            entry.level = "known_well"
            profile.known_well.append(entry)
        else:
            entry.level = "seen"
            profile.seen.append(entry)

    if project.path:
        _detect_gaps(project, concepts, profile)

    profile.total = len(profile.known_well) + len(profile.seen) + len(profile.gaps)
    return profile


def _detect_gaps(project, concepts, profile: ExpertiseProfile) -> None:
    path = Path(project.path)
    if not path.is_dir():
        return

    scanned = scan_npm(path)
    scanned.merge(scan_python(path))

    existing_names = {c.name.lower() for c in concepts}
    for sc in scanned.concepts:
        if sc.name.lower() not in existing_names:
            profile.gaps.append(ExpertiseEntry(
                name=sc.name, level="gap", category=sc.category_hint,
                signals=[f"in {sc.source}, not in graph"],
            ))
