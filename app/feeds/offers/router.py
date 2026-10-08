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
from app.security import require_recommendation_key

router = APIRouter(
    prefix="/feeds/offers",
    tags=["feeds"],
    dependencies=[Depends(require_recommendation_key)],
)
public_router = APIRouter(prefix="/public/feeds/offers", tags=["public-feeds"])


def get_service(
    graph: Annotated[GraphService, Depends(get_graph)],
    postgres: Annotated[PostgresService, Depends(get_postgres)],
) -> OffersService:
    return OffersService(graph, postgres)


@router.get("", response_model=FeedResponse[OfferItem])
async def offers_feed(
    service: Annotated[OffersService, Depends(get_service)],
    strategy: Annotated[OfferStrategy, Query()] = OfferStrategy.BEST_VALUE,
    local_unit_id: Annotated[UUID | None, Query()] = None,
    company_id: Annotated[UUID | None, Query()] = None,
):
    result = await service.recommend(strategy, local_unit_id)
    return build_response("offers", strategy.value, company_id, result)


@public_router.get("", response_model=PublicFeedResponse[PublicOffer])
async def public_offers_feed(
    response: Response,
    service: Annotated[OffersService, Depends(get_service)],
):
    set_public_cache(response)
    return build_public_response(await service.public())
