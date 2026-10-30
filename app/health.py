import asyncio
import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.database import PostgresService
from app.dependencies import get_postgres
from app.version import VERSION

logger = logging.getLogger(__name__)

READY_TIMEOUT_SECONDS = 2

router = APIRouter(tags=["Saúde"])


class HealthResponse(BaseModel):
    status: Literal["UP"] = Field(description="O processo está vivo.")
    version: str = Field(description="Versão do release em execução.", examples=["0.3.0"])


class ReadyResponse(BaseModel):
    status: Literal["UP", "DOWN"] = Field(description="UP quando o PostgreSQL responde; DOWN caso contrário.")


async def _ping(postgres: PostgresService) -> None:
    async with postgres.connection() as connection:
        await connection.fetchval("SELECT 1")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Indica se o processo está vivo",
    description="Não consulta nenhuma dependência.",
    operation_id="getHealth",
    openapi_extra={"security": [], "x-error-codes": ["INTERNAL_ERROR"]},
)
async def health():
    return {"status": "UP", "version": VERSION}


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Indica se o serviço está pronto para atender",
    description=(
        "Consulta só o PostgreSQL. O grafo fica de fora: sem ele, os feeds respondem pelo fallback SQL."
    ),
    operation_id="getReady",
    responses={503: {"description": "O PostgreSQL não respondeu.", "model": ReadyResponse}},
    openapi_extra={"security": [], "x-error-codes": ["INTERNAL_ERROR"]},
)
async def ready(postgres: Annotated[PostgresService, Depends(get_postgres)]):
    try:
        await asyncio.wait_for(_ping(postgres), timeout=READY_TIMEOUT_SECONDS)
    except Exception:
        logger.exception("Falha no readiness check do PostgreSQL")
        return JSONResponse({"status": "DOWN"}, status_code=503)
    return {"status": "UP"}
