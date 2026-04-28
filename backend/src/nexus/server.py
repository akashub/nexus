from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from nexus.db import get_connection, init_db


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
    name: str
    category: str | None = None
    tags: list[str] | None = None
    notes: str | None = None
    no_enrich: bool = False


class ConceptUpdate(BaseModel):
    description: str | None = None
    summary: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    notes: str | None = None


class EdgeCreate(BaseModel):
    source_id: str
    target_id: str
    relationship: str = "related_to"
    description: str | None = None


class AskRequest(BaseModel):
    question: str


def concept_to_dict(c) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "summary": c.summary,
        "category": c.category,
        "tags": c.tags,
        "source": c.source,
        "notes": c.notes,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


def edge_to_dict(e) -> dict:
    return {
        "id": e.id,
        "source_id": e.source_id,
        "target_id": e.target_id,
        "relationship": e.relationship,
        "description": e.description,
        "weight": e.weight,
        "created_at": e.created_at,
    }


from nexus.routes import router  # noqa: E402

app.include_router(router, prefix="/api")
