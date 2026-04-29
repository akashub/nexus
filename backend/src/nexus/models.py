from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Concept:
    id: str
    name: str
    description: str | None = None
    summary: str | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    source: str = "manual"
    embedding: bytes | None = None
    notes: str | None = None
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_row(cls, row: dict) -> Concept:
        tags_raw = row.get("tags") or "[]"
        tags = json.loads(tags_raw) if isinstance(tags_raw, str) else tags_raw
        return cls(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            summary=row.get("summary"),
            category=row.get("category"),
            tags=tags,
            source=row.get("source", "manual"),
            embedding=row.get("embedding"),
            notes=row.get("notes"),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )


@dataclass
class Edge:
    id: str
    source_id: str
    target_id: str
    relationship: str
    description: str | None = None
    weight: float = 1.0
    created_at: str = ""

    @classmethod
    def from_row(cls, row: dict) -> Edge:
        return cls(
            id=row["id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            relationship=row["relationship"],
            description=row.get("description"),
            weight=row.get("weight", 1.0),
            created_at=row.get("created_at", ""),
        )


@dataclass
class Conversation:
    id: str
    question: str
    answer: str
    related_concepts: list[str] = field(default_factory=list)
    created_at: str = ""

    @classmethod
    def from_row(cls, row: dict) -> Conversation:
        rc_raw = row.get("related_concepts") or "[]"
        rc = json.loads(rc_raw) if isinstance(rc_raw, str) else rc_raw
        return cls(
            id=row["id"],
            question=row["question"],
            answer=row["answer"],
            related_concepts=rc,
            created_at=row.get("created_at", ""),
        )
