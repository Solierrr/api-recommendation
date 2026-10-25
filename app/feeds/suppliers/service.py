from pathlib import Path
from uuid import UUID

from app.config import settings
from app.database import GraphService
from app.feeds import graph
from app.feeds.common import FeedResult, FeedSource, bounded
from app.feeds.suppliers.strategies import SupplierStrategy, rank_suppliers
from app.queries import load

_DIRECTORY = Path(__file__).parent


class SuppliersService:
    def __init__(self, graph_service: GraphService) -> None:
        self.graph = graph_service

    async def public(self) -> list[dict]:
        return (await self.recommend(SupplierStrategy.MOST_PROVEN, None)).items

    async def recommend(self, strategy: SupplierStrategy, local_unit_id: UUID | None) -> FeedResult:
        async with self.graph.read_session() as session:
            snapshot = await graph.active_snapshot(session)
            version = snapshot["active_version"]
            context = None
            if local_unit_id is not None:
                context = await graph.local_unit_context(session, version, str(local_unit_id))
            candidates = bounded(
                await graph.fetch_all(
                    session,
                    load(_DIRECTORY / "candidates.cypher"),
                    sync_version=version,
                    fetch_limit=settings.RECOMMENDATION_POOL_LIMIT + 1,
                ),
                settings.RECOMMENDATION_POOL_LIMIT,
            )
        items = rank_suppliers(strategy, context, candidates, settings.RECOMMENDATION_RESULT_LIMIT)
        return FeedResult(FeedSource.GRAPH, version, items, [])
