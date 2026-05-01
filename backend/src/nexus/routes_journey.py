from __future__ import annotations

from fastapi import APIRouter, Query

from nexus.db_concepts import get_journey
from nexus.server import ConnDep, concept_dict

router = APIRouter()


@router.get("/journey")
def journey_route(
    conn: ConnDep,
    project_id: str | None = None,
    days: int = Query(default=90, ge=1, le=3650),
):
    weeks = get_journey(conn, project_id=project_id, days=days)
    return [
        {
            "week": w["week"],
            "week_start": w["week_start"],
            "concepts": [concept_dict(c) for c in w["concepts"]],
        }
        for w in weeks
    ]
