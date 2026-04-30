from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScannedConcept:
    name: str
    source: str
    category_hint: str | None = None
    context: str | None = None
    is_dev_dep: bool = False
    setup_command: str | None = None


@dataclass
class ScannedRelationship:
    source_name: str
    target_name: str
    relationship: str
    reason: str | None = None


@dataclass
class ScanResult:
    concepts: list[ScannedConcept] = field(default_factory=list)
    relationships: list[ScannedRelationship] = field(default_factory=list)
    project_description: str | None = None

    def merge(self, other: ScanResult) -> None:
        seen = {c.name.lower() for c in self.concepts}
        for c in other.concepts:
            if c.name.lower() not in seen:
                self.concepts.append(c)
                seen.add(c.name.lower())
        self.relationships.extend(other.relationships)
        if other.project_description and not self.project_description:
            self.project_description = other.project_description
