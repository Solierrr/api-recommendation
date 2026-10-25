from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.database import GraphService
from app.dependencies import get_graph
from app.errors import GraphUnavailableError, SnapshotUnavailableError
from app.feeds import graph as graph_queries

router = APIRouter(tags=["health"])

GraphStatus = Literal["ready", "unavailable", "no_snapshot", "disabled"]


class LivenessResponse(BaseModel):
    status: Literal["alive"]


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    graph: GraphStatus
    active_sync_version: UUID | None = None
    snapshot_age_seconds: int | None = None


async def _graph_status(graph: GraphService) -> dict:
    if not graph.configured:
        return {"graph": "disabled"}
    try:
        async with graph.read_session() as session:
            snapshot = await graph_queries.active_snapshot(session)
    except SnapshotUnavailableError:
        return {"graph": "no_snapshot"}
    except GraphUnavailableError:
        return {"graph": "unavailable"}
    return {
        "graph": "ready",
        "active_sync_version": snapshot["active_version"],
        "snapshot_age_seconds": snapshot["snapshot_age_seconds"],
    }


@router.get("/health/live", response_model=LivenessResponse)
async def liveness_check():
    return {"status": "alive"}


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_check(graph: Annotated[GraphService, Depends(get_graph)]):
    return {"status": "ready", **await _graph_status(graph)}
