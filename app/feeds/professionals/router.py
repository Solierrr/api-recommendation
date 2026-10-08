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
from app.security import require_recommendation_key

router = APIRouter(
    prefix="/feeds/professionals",
    tags=["feeds"],
    dependencies=[Depends(require_recommendation_key)],
)
public_router = APIRouter(prefix="/public/feeds/professionals", tags=["public-feeds"])


def get_service(
    graph: Annotated[GraphService, Depends(get_graph)],
    postgres: Annotated[PostgresService, Depends(get_postgres)],
) -> ProfessionalsService:
    return ProfessionalsService(graph, postgres)


@router.get("", response_model=FeedResponse[ProfessionalItem])
async def professionals_feed(
    service: Annotated[ProfessionalsService, Depends(get_service)],
    strategy: Annotated[ProfessionalStrategy, Query()] = ProfessionalStrategy.BEST_MATCH,
    profession_id: Annotated[UUID | None, Query()] = None,
    company_id: Annotated[UUID | None, Query()] = None,
):
    result = await service.recommend(strategy, profession_id)
    return build_response("professionals", strategy.value, company_id, result)


@public_router.get("", response_model=PublicFeedResponse[PublicProfessional])
async def public_professionals_feed(
    response: Response,
    service: Annotated[ProfessionalsService, Depends(get_service)],
    profession_id: Annotated[UUID | None, Query()] = None,
):
    set_public_cache(response)
    return build_public_response(await service.public(profession_id))
