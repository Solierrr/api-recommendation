from pathlib import Path
from uuid import UUID

from app.config import settings
from app.database import GraphService
from app.errors import ContextNotFoundError
from app.feeds import graph
from app.feeds.common import FeedResult, FeedSource, bounded
from app.feeds.professionals.strategies import ProfessionalStrategy, rank_professionals
from app.queries import load

_DIRECTORY = Path(__file__).parent
_GRAPH_WARNING = (
    "Avaliações e experiência são globais por técnico porque o api-core ainda não as relaciona "
    "diretamente à profissão."
)


class ProfessionalsService:
    def __init__(self, graph_service: GraphService) -> None:
        self.graph = graph_service

    async def public(self, profession_id: UUID | None) -> list[dict]:
        return (await self.recommend(ProfessionalStrategy.TOP_RATED, profession_id)).items

    async def recommend(self, strategy: ProfessionalStrategy, profession_id: UUID | None) -> FeedResult:
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
