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
from app.feeds.suppliers.schemas import PublicSupplier, SupplierItem
from app.feeds.suppliers.service import SuppliersService
from app.feeds.suppliers.strategies import SupplierStrategy
from app.security import require_recommendation_key

router = APIRouter(
    prefix="/feeds/suppliers",
    tags=["feeds"],
    dependencies=[Depends(require_recommendation_key)],
)
public_router = APIRouter(prefix="/public/feeds/suppliers", tags=["public-feeds"])


def get_service(
    graph: Annotated[GraphService, Depends(get_graph)],
    postgres: Annotated[PostgresService, Depends(get_postgres)],
) -> SuppliersService:
    return SuppliersService(graph, postgres)


@router.get("", response_model=FeedResponse[SupplierItem])
async def suppliers_feed(
    service: Annotated[SuppliersService, Depends(get_service)],
    strategy: Annotated[SupplierStrategy, Query()] = SupplierStrategy.MOST_PROVEN,
    local_unit_id: Annotated[UUID | None, Query()] = None,
    company_id: Annotated[UUID | None, Query()] = None,
):
    result = await service.recommend(strategy, local_unit_id)
    return build_response("suppliers", strategy.value, company_id, result)


@public_router.get("", response_model=PublicFeedResponse[PublicSupplier])
async def public_suppliers_feed(
    response: Response,
    service: Annotated[SuppliersService, Depends(get_service)],
):
    set_public_cache(response)
    return build_public_response(await service.public())
