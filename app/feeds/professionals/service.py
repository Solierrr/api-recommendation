from pathlib import Path
from uuid import UUID

from app.config import settings
from app.database import GraphService, PostgresService
from app.errors import ContextNotFoundError
from app.feeds import fallback, graph
from app.feeds.common import FeedResult, FeedSource, bounded, graph_or_fallback
from app.feeds.professionals.strategies import ProfessionalStrategy, rank_professionals
from app.queries import load

_DIRECTORY = Path(__file__).parent
_FALLBACK_WARNING = (
    "O grafo está indisponível; o resultado é uma amostra dos profissionais mais bem avaliados, "
    "sem aplicar a estratégia pedida."
)
_GRAPH_WARNING = (
    "Avaliações e experiência são globais por técnico porque o api-core ainda não as relaciona "
    "diretamente à profissão."
)


class ProfessionalsService:
    def __init__(self, graph_service: GraphService, postgres: PostgresService) -> None:
        self.graph = graph_service
        self.postgres = postgres

    async def recommend(self, strategy: ProfessionalStrategy, profession_id: UUID | None) -> FeedResult:
        return await graph_or_fallback(
            lambda: self._from_graph(strategy, profession_id),
            lambda: self._from_fallback(profession_id),
            _FALLBACK_WARNING,
        )

    async def public(self, profession_id: UUID | None) -> list[dict]:
        return await self._from_fallback(profession_id)

    async def _from_graph(self, strategy: ProfessionalStrategy, profession_id: UUID | None) -> FeedResult:
        async with self.graph.read_session() as session:
            snapshot = await graph.active_snapshot(session)
            version = snapshot["active_version"]
            if profession_id is not None:
                context = await graph.fetch_one(
                    session,
                    load(_DIRECTORY / "context.cypher"),
                    sync_version=version,
                    context_id=str(profession_id),
                )
                if context is None:
                    raise ContextNotFoundError(
                        "PROFESSION_NOT_FOUND", "A profissão não existe no snapshot ativo."
                    )
            candidates = bounded(
                await graph.fetch_all(
                    session,
                    load(_DIRECTORY / "candidates.cypher"),
                    sync_version=version,
                    profession_id=str(profession_id) if profession_id else None,
                    fetch_limit=settings.RECOMMENDATION_POOL_LIMIT + 1,
                ),
                settings.RECOMMENDATION_POOL_LIMIT,
            )
        items = rank_professionals(strategy, candidates, settings.RECOMMENDATION_RESULT_LIMIT)
        return FeedResult(FeedSource.GRAPH, version, items, [_GRAPH_WARNING])

    async def _from_fallback(self, profession_id: UUID | None) -> list[dict]:
        rows = await fallback.sample(
            self.postgres,
            _DIRECTORY / "fallback.sql",
            settings.FALLBACK_POOL_SIZE,
            settings.RECOMMENDATION_RESULT_LIMIT,
            profession_id,
        )
        return fallback.decorate(
            rows,
            unit="average_rating_0_5",
            reason="Selecionado entre os profissionais mais bem avaliados",
            value_field="average_rating_global",
        )
