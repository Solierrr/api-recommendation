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
from app.feeds.offers.schemas import OfferItem, PublicOffer
from app.feeds.offers.service import OffersService
from app.feeds.offers.strategies import OfferStrategy
from app.security import require_caller

router = APIRouter(
    prefix="/feeds/offers",
    tags=["Feeds"],
    dependencies=[Depends(require_caller("mcp-database"))],
)
public_router = APIRouter(prefix="/public/feeds/offers", tags=["Feeds públicos"])


def get_service(
    graph: Annotated[GraphService, Depends(get_graph)],
    postgres: Annotated[PostgresService, Depends(get_postgres)],
) -> OffersService:
    return OffersService(graph, postgres)


@router.get(
    "",
    response_model=FeedResponse[OfferItem],
    summary="Lista ofertas de placas solares ranqueadas pela estratégia pedida",
    description=(
        "Chamado por serviço (mcp-database) com a chave no cabeçalho X-Service-Key. "
        "Sem o grafo, responde com source=fallback: uma amostra do PostgreSQL, sem aplicar a estratégia."
    ),
    operation_id="getOffersFeed",
    responses={
        401: {"description": "Chave de serviço ausente ou inválida."},
        403: {"description": "Serviço chamador não autorizado nesta rota."},
        404: {"description": "A unidade local não existe no snapshot ativo."},
        422: {
            "description": "Parâmetro inválido, unidade sem geolocalização única, estratégia sem local_unit_id ou conjunto elegível acima do limite de ranking."
        },
        503: {"description": "Nem o grafo nem o PostgreSQL responderam."},
    },
    openapi_extra={
        "x-error-codes": [
            "UNAUTHENTICATED",
            "FORBIDDEN",
            "VALIDATION_FAILED",
            "LOCAL_UNIT_REQUIRED",
            "LOCAL_UNIT_NOT_FOUND",
            "LOCAL_UNIT_GEO_REQUIRED",
            "LOCAL_UNIT_GEO_AMBIGUOUS",
            "CANDIDATE_POOL_TOO_LARGE",
            "FEED_UNAVAILABLE",
            "INTERNAL_ERROR",
        ]
    },
)
async def offers_feed(
    service: Annotated[OffersService, Depends(get_service)],
    strategy: Annotated[
        OfferStrategy, Query(description="Critério de ordenação do feed.")
    ] = OfferStrategy.BEST_VALUE,
    local_unit_id: Annotated[
        UUID | None,
        Query(
            description="Unidade local de referência para calcular distância; obrigatória na estratégia nearest_available."
        ),
    ] = None,
    company_id: Annotated[
        UUID | None, Query(description="Empresa que vê o feed; ainda não influencia o ranking.")
    ] = None,
):
    result = await service.recommend(strategy, local_unit_id)
    return build_response("offers", strategy.value, company_id, result)


@public_router.get(
    "",
    response_model=PublicFeedResponse[PublicOffer],
    summary="Lista uma amostra pública de ofertas de placas solares",
    description=(
        "Aberto, sem chave. Nunca consulta o grafo e responde com Cache-Control público "
        "(e stale-if-error) para a Cloudflare atender os anônimos."
    ),
    operation_id="getPublicOffersFeed",
    responses={
        503: {"description": "O PostgreSQL não respondeu."},
    },
    openapi_extra={"security": [], "x-error-codes": ["FEED_UNAVAILABLE", "INTERNAL_ERROR"]},
)
async def public_offers_feed(
    response: Response,
    service: Annotated[OffersService, Depends(get_service)],
):
    set_public_cache(response)
    return build_public_response(await service.public())
