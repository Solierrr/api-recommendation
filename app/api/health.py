import logging
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status
from neo4j import AsyncSession

from app.config import settings
from app.database import neo4j_service, postgres_service
from app.repositories.graph_sync_repository import GraphSyncRepository
from app.schemas.responses import HealthResponse, LivenessResponse, ReadinessResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

READINESS_QUERY = """
    MATCH (state:SyncState {source: $source})
    WHERE state.active_version IS NOT NULL
      AND state.activated_at IS NOT NULL
    OPTIONAL MATCH (node)
    WHERE node.source = $source
      AND node.sync_version = state.active_version
    WITH state, count(node) AS node_count
    RETURN state.active_version AS active_version,
           node_count,
           toInteger(
               duration.inSeconds(state.activated_at, datetime()).seconds
           ) AS snapshot_age_seconds
"""


async def _readiness_status(
    connection: asyncpg.Connection,
    session: AsyncSession,
) -> dict:
    postgres_status = await connection.fetchval("SELECT 1")
    result = await session.run(
        READINESS_QUERY,
        source=GraphSyncRepository.SOURCE,
    )
    record = await result.single()
    if postgres_status != 1 or record is None:
        raise RuntimeError("Dependência indisponível ou snapshot ausente")

    snapshot_age_seconds = int(record["snapshot_age_seconds"])
    node_count = int(record["node_count"])
    if (
        snapshot_age_seconds < 0
        or snapshot_age_seconds > settings.SNAPSHOT_MAX_AGE_SECONDS
        or node_count <= 0
    ):
        raise RuntimeError("Snapshot ausente, vazio ou desatualizado")

    return {
        "status": "ready",
        "postgres": "connected",
        "neo4j": "connected",
        "active_sync_version": record["active_version"],
        "snapshot_age_seconds": snapshot_age_seconds,
        "snapshot_node_count": node_count,
    }


async def _checked_readiness(
    connection: asyncpg.Connection,
    session: AsyncSession,
) -> dict:
    try:
        return await _readiness_status(connection, session)
    except Exception:
        logger.exception("Falha no readiness check")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço indisponível: dependência ou snapshot não está pronto",
        ) from None


@router.get("/health/live", response_model=LivenessResponse)
async def liveness_check():
    return {"status": "alive"}


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_check(
    connection: Annotated[asyncpg.Connection, Depends(postgres_service.get_connection)],
    session: Annotated[AsyncSession, Depends(neo4j_service.get_read_session)],
):
    return await _checked_readiness(connection, session)


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    deprecated=True,
)
async def health_check(
    connection: Annotated[asyncpg.Connection, Depends(postgres_service.get_connection)],
    session: Annotated[AsyncSession, Depends(neo4j_service.get_read_session)],
):
    await _checked_readiness(connection, session)
    return {
        "status": "online",
        "postgres": "connected",
        "neo4j": "connected",
    }
