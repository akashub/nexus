from __future__ import annotations

import json
from dataclasses import dataclass, field

RELATIONSHIP_TYPES = frozenset({
    "uses", "depends_on", "similar_to", "part_of", "related_to",
    "sends_data_to", "triggers", "builds_into", "configured_by",
    "tested_with", "wraps", "serves", "deployed_via", "replaces",
})


@dataclass
class Project:
    id: str
    name: str
    path: str | None = None
    description: str | None = None
    last_scanned_at: str | None = None
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_row(cls, row: dict) -> Project:
        return cls(
            id=row["id"], name=row["name"], path=row.get("path"),
            description=row.get("description"),
            last_scanned_at=row.get("last_scanned_at"),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )


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
    quickstart: str | None = None
    doc_url: str | None = None
    context7_id: str | None = None
    enrich_status: str | None = None
    project_id: str | None = None
    semantic_group: str | None = None
    setup_commands: list[str] = field(default_factory=list)
    config_files: list[dict] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_row(cls, row: dict) -> Concept:
        tags_raw = row.get("tags") or "[]"
        tags = json.loads(tags_raw) if isinstance(tags_raw, str) else tags_raw
        setup_raw = row.get("setup_commands") or "[]"
        setup = json.loads(setup_raw) if isinstance(setup_raw, str) else setup_raw
        config_raw = row.get("config_files") or "[]"
        config = json.loads(config_raw) if isinstance(config_raw, str) else config_raw
        return cls(
            id=row["id"], name=row["name"],
            description=row.get("description"), summary=row.get("summary"),
            category=row.get("category"), tags=tags,
            source=row.get("source", "manual"), embedding=row.get("embedding"),
            notes=row.get("notes"), quickstart=row.get("quickstart"),
            doc_url=row.get("doc_url"), context7_id=row.get("context7_id"),
            enrich_status=row.get("enrich_status"),
            project_id=row.get("project_id"),
            semantic_group=row.get("semantic_group"),
            setup_commands=setup, config_files=config,
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
