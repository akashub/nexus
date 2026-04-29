from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from nexus.db import get_connection, init_db
from nexus.models import Concept, Edge


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Nexus", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",
        "http://localhost:5173",
        "http://127.0.0.1:1420",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_conn():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


ConnDep = Annotated[sqlite3.Connection, Depends(_get_conn)]


class ConceptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=50)
    tags: list[str] | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=5000)
    no_enrich: bool = False


class ConceptUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=5000)
    summary: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=50)
    tags: list[str] | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=5000)


class EdgeCreate(BaseModel):
    source_id: str = Field(max_length=36)
    target_id: str = Field(max_length=36)
    relationship: str = Field(default="related_to", max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


def concept_dict(c: Concept) -> dict:
    return {
        "id": c.id, "name": c.name, "description": c.description,
        "summary": c.summary, "category": c.category, "tags": c.tags,
        "source": c.source, "notes": c.notes,
        "quickstart": c.quickstart, "doc_url": c.doc_url,
        "context7_id": c.context7_id, "enrich_status": c.enrich_status,
        "created_at": c.created_at, "updated_at": c.updated_at,
    }


def edge_dict(e: Edge) -> dict:
    return {
        "id": e.id, "source_id": e.source_id, "target_id": e.target_id,
        "relationship": e.relationship, "description": e.description,
        "weight": e.weight, "created_at": e.created_at,
    }


from nexus.routes import router  # noqa: E402

app.include_router(router, prefix="/api")
