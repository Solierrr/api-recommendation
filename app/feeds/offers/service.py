from pathlib import Path
from uuid import UUID

from app.config import settings
from app.database import GraphService, PostgresService
from app.feeds import fallback, graph
from app.feeds.common import FeedResult, FeedSource, bounded, graph_or_fallback
from app.feeds.offers.strategies import OfferStrategy, rank_offers, with_prices
from app.queries import load

_DIRECTORY = Path(__file__).parent
_FALLBACK_WARNING = (
    "O grafo está indisponível; o resultado é uma amostra das ofertas de melhor custo por Wp, "
    "sem aplicar a estratégia pedida."
)
_GLOBAL_WARNING = (
    "Com os dados atuais, esta estratégia valida a unidade, mas classifica o catálogo global elegível."
)


class OffersService:
    def __init__(self, graph_service: GraphService, postgres: PostgresService) -> None:
        self.graph = graph_service
        self.postgres = postgres

    async def recommend(self, strategy: OfferStrategy, local_unit_id: UUID | None) -> FeedResult:
        return await graph_or_fallback(
            lambda: self._from_graph(strategy, local_unit_id),
            self._from_fallback,
            _FALLBACK_WARNING,
        )

    async def public(self) -> list[dict]:
        return await self._from_fallback()

    async def _from_graph(self, strategy: OfferStrategy, local_unit_id: UUID | None) -> FeedResult:
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
        items = rank_offers(strategy, context, candidates, settings.RECOMMENDATION_RESULT_LIMIT)
        warnings = [] if strategy is OfferStrategy.NEAREST_AVAILABLE else [_GLOBAL_WARNING]
        return FeedResult(FeedSource.GRAPH, version, items, warnings)

    async def _from_fallback(self) -> list[dict]:
        rows = await fallback.sample(
            self.postgres,
            _DIRECTORY / "fallback.sql",
            settings.FALLBACK_POOL_SIZE,
            settings.RECOMMENDATION_RESULT_LIMIT,
        )
        return fallback.decorate(
            with_prices(rows),
            unit="BRL_per_Wp",
            reason="Selecionada entre as ofertas de melhor custo por Wp",
            value_field="price_per_wp",
        )
