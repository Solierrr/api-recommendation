from neo4j import AsyncSession

from app.core.candidate_service import CandidateService
from app.core.ranking_service import RankingService


class RecommendationService:
    def __init__(self, session: AsyncSession):
        self.candidate_service = CandidateService(session)

    async def get_recommendations(self, service_name: str, min_level: int = 2, limit: int = 5) -> list[dict]:
        """
        Pipeline Completo: Busca -> Scoring -> Ordenação -> Top N
        """
        # 1. Recupera o pool pré-filtrado do grafo
        candidates = await self.candidate_service.fetch_candidate_pool(service_name, min_level)
        
        # 2. Aplica o cálculo de score e motivos individualmente
        scored_candidates = [
            RankingService.calculate_score(c) for c in candidates
        ]
        
        # 3. Re-ordena o resultado final do maior score para o menor
        ranked_candidates = sorted(
            scored_candidates, 
            key=lambda x: x["score"], 
            reverse=True
        )
        
        # 4. Retorna apenas os N melhores resultados
        return ranked_candidates[:limit]
