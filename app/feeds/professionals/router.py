from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.database import GraphService, PostgresService
from app.dependencies import get_graph, get_postgres
from app.feeds.common import (
    FeedResponse,
    PublicFeedResponse,
    build_public_response,
    build_response,
    set_public_cache,
)
from app.feeds.professionals.schemas import ProfessionalItem, PublicProfessional
from app.feeds.professionals.service import ProfessionalsService
from app.feeds.professionals.strategies import ProfessionalStrategy
from app.security import require_caller

router = APIRouter(
    prefix="/feeds/professionals",
    tags=["Feeds"],
    dependencies=[Depends(require_caller("mcp-database"))],
)
public_router = APIRouter(prefix="/public/feeds/professionals", tags=["Feeds públicos"])


def get_service(
    graph: Annotated[GraphService, Depends(get_graph)],
    postgres: Annotated[PostgresService, Depends(get_postgres)],
) -> ProfessionalsService:
    return ProfessionalsService(graph, postgres)


@router.get(
    "",
    response_model=FeedResponse[ProfessionalItem],
    summary="Lista profissionais ranqueados pela estratégia pedida",
    description=(
        "Chamado por serviço (mcp-database) com a chave no cabeçalho X-Service-Key. "
        "Sem o grafo, responde com source=fallback: uma amostra do PostgreSQL, sem aplicar a estratégia."
    ),
    operation_id="getProfessionalsFeed",
    responses={
        401: {"description": "Chave de serviço ausente ou inválida."},
        403: {"description": "Serviço chamador não autorizado nesta rota."},
        404: {"description": "A profissão não existe no snapshot ativo."},
        422: {"description": "Parâmetro inválido ou conjunto elegível acima do limite de ranking."},
        503: {"description": "Nem o grafo nem o PostgreSQL responderam."},
    },
    openapi_extra={
        "x-error-codes": [
            "UNAUTHENTICATED",
            "FORBIDDEN",
            "VALIDATION_FAILED",
            "PROFESSION_NOT_FOUND",
            "CANDIDATE_POOL_TOO_LARGE",
            "FEED_UNAVAILABLE",
            "INTERNAL_ERROR",
        ]
    },
)
async def professionals_feed(
    service: Annotated[ProfessionalsService, Depends(get_service)],
    strategy: Annotated[
        ProfessionalStrategy, Query(description="Critério de ordenação do feed.")
    ] = ProfessionalStrategy.BEST_MATCH,
    profession_id: Annotated[
        UUID | None, Query(description="Filtra pela profissão; precisa existir no snapshot ativo do grafo.")
    ] = None,
    company_id: Annotated[
        UUID | None, Query(description="Empresa que vê o feed; ainda não influencia o ranking.")
    ] = None,
):
    result = await service.recommend(strategy, profession_id)
    return build_response("professionals", strategy.value, company_id, result)


@public_router.get(
    "",
    response_model=PublicFeedResponse[PublicProfessional],
    summary="Lista uma amostra pública de profissionais",
    description=(
        "Aberto, sem chave. Nunca consulta o grafo e responde com Cache-Control público "
        "(e stale-if-error) para a Cloudflare atender os anônimos."
    ),
    operation_id="getPublicProfessionalsFeed",
    responses={
        422: {"description": "Parâmetro inválido."},
        503: {"description": "O PostgreSQL não respondeu."},
    },
    openapi_extra={
        "security": [],
        "x-error-codes": ["VALIDATION_FAILED", "FEED_UNAVAILABLE", "INTERNAL_ERROR"],
    },
)
async def public_professionals_feed(
    response: Response,
    service: Annotated[ProfessionalsService, Depends(get_service)],
    profession_id: Annotated[
        UUID | None, Query(description="Filtra pela profissão; precisa existir no snapshot ativo do grafo.")
    ] = None,
):
    set_public_cache(response)
    return build_public_response(await service.public(profession_id))
