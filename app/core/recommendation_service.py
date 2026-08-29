from datetime import UTC, datetime
from uuid import UUID

from neo4j import AsyncSession

from app.config import settings
from app.core.candidate_service import CandidateService
from app.core.errors import (
    ContextNotFoundError,
    RecommendationDataUnavailableError,
    SnapshotUnavailableError,
)
from app.core.ranking_service import RankingService
from app.core.recommendation_engine import RecommendationEngine
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.recommendations import (
    PanelStrategy,
    ProfessionalStrategy,
    TechnicianStrategy,
)


class RecommendationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.candidate_service = CandidateService(session)

    async def _active_version(self) -> str:
        version = await RecommendationRepository.get_active_version(self.session)
        if version is None:
            raise SnapshotUnavailableError(
                "SNAPSHOT_UNAVAILABLE",
                "Nenhum snapshot de recomendação está ativo.",
            )
        return version

    @staticmethod
    def _context(
        context_type: str,
        context_id: UUID,
        strategy: str,
        version: str,
    ) -> dict:
        return {
            "type": context_type,
            "id": context_id,
            "strategy": strategy,
            "generated_at": datetime.now(UTC),
            "sync_version": version,
        }

    @staticmethod
    def _bounded_candidates(candidates: list[dict]) -> list[dict]:
        if len(candidates) > settings.RECOMMENDATION_POOL_LIMIT:
            raise RecommendationDataUnavailableError(
                "CANDIDATE_POOL_TOO_LARGE",
                "O conjunto elegível excede o limite seguro para ranking global; "
                "refine o contexto ou aumente o limite operacional.",
            )
        return candidates

    async def recommend_panels(
        self, local_unit_id: UUID, strategy: PanelStrategy
    ) -> dict:
        version = await self._active_version()
        context = await RecommendationRepository.get_panel_context(
            self.session, version, str(local_unit_id)
        )
        if context is None:
            raise ContextNotFoundError(
                "LOCAL_UNIT_NOT_FOUND",
                "A unidade local não existe no snapshot ativo.",
            )
        candidates = self._bounded_candidates(
            await RecommendationRepository.get_panel_candidates(
                self.session,
                version,
                settings.RECOMMENDATION_POOL_LIMIT,
            )
        )
        items, warnings = RecommendationEngine.rank_panels(
            strategy,
            context,
            candidates,
            settings.RECOMMENDATION_RESULT_LIMIT,
        )
        if strategy not in {PanelStrategy.NEAREST_AVAILABLE}:
            warnings.append(
                "Com os dados atuais, esta estratégia valida a unidade, "
                "mas classifica o catálogo global elegível."
            )
        return {
            "context": self._context(
                "local_unit", local_unit_id, strategy.value, version
            ),
            "items": items,
            "warnings": warnings,
        }

    async def recommend_professionals(
        self, profession_id: UUID, strategy: ProfessionalStrategy
    ) -> dict:
        version = await self._active_version()
        context = await RecommendationRepository.get_profession_context(
            self.session, version, str(profession_id)
        )
        if context is None:
            raise ContextNotFoundError(
                "PROFESSION_NOT_FOUND",
                "A profissão não existe no snapshot ativo.",
            )
        candidates = self._bounded_candidates(
            await RecommendationRepository.get_professional_candidates(
                self.session,
                version,
                str(profession_id),
                settings.RECOMMENDATION_POOL_LIMIT,
            )
        )
        items = RecommendationEngine.rank_professionals(
            strategy,
            candidates,
            settings.RECOMMENDATION_RESULT_LIMIT,
        )
        return {
            "context": self._context(
                "profession", profession_id, strategy.value, version
            ),
            "items": items,
            "warnings": [
                "Avaliações e experiência são globais por técnico porque o "
                "api-core ainda não as relaciona diretamente à profissão."
            ],
        }

    async def recommend_technicians(
        self, technical_service_id: UUID, strategy: TechnicianStrategy
    ) -> dict:
        version = await self._active_version()
        context = await RecommendationRepository.get_technical_service_context(
            self.session, version, str(technical_service_id)
        )
        if context is None:
            raise ContextNotFoundError(
                "TECHNICAL_SERVICE_NOT_FOUND",
                "O serviço técnico não existe no snapshot ativo.",
            )
        if context["status"] in {"COMPLETED", "CANCELED"}:
            raise RecommendationDataUnavailableError(
                "SERVICE_NOT_ASSIGNABLE",
                "Serviços concluídos ou cancelados não aceitam recomendação de executor.",
            )
        if not context["normalized_purpose"]:
            raise RecommendationDataUnavailableError(
                "SERVICE_PURPOSE_REQUIRED",
                "O serviço precisa de um purpose não vazio.",
            )
        candidates = self._bounded_candidates(
            await RecommendationRepository.get_technician_candidates(
                self.session,
                version,
                str(technical_service_id),
                context["normalized_purpose"],
                settings.RECOMMENDATION_POOL_LIMIT,
            )
        )
        items, warnings = RecommendationEngine.rank_technicians(
            strategy,
            context,
            candidates,
            settings.RECOMMENDATION_RESULT_LIMIT,
            settings.APP_TIMEZONE,
        )
        return {
            "context": self._context(
                "technical_service",
                technical_service_id,
                strategy.value,
                version,
            ),
            "items": items,
            "warnings": warnings,
        }

    async def get_recommendations(
        self,
        service_name: str,
        min_rating: float = 0,
        limit: int = 5,
    ) -> list[dict]:
        """Compatibilidade do endpoint legado /candidates/{service_name}."""
        candidates = await self.candidate_service.fetch_candidate_pool(
            service_name,
            min_rating,
        )
        scored_candidates = [
            RankingService.calculate_score(candidate) for candidate in candidates
        ]
        ranked_candidates = sorted(
            scored_candidates,
            key=lambda candidate: (
                candidate["score"],
                candidate["review_count"],
            ),
            reverse=True,
        )
        return ranked_candidates[:limit]
