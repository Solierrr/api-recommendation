from neo4j import AsyncSession

from app.repositories.candidate_repository import CandidateRepository


class CandidateService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_candidate_pool(self, service_name: str, min_level: int = 2) -> list[dict]:
        """
        Orquestra a busca e aplica estratégia de fallback (Cold Start).
        """
        # 1. Tenta buscar candidatos com o filtro ideal
        candidates = await CandidateRepository.find_candidates_by_service(
            session=self.session,
            service_name=service_name,
            min_qualification_level=min_level
        )

        # 2. Estratégia de Cold Start / Fallback: Se não encontrar ninguém, relaxa o nível mínimo
        if not candidates and min_level > 1:
            candidates = await CandidateRepository.find_candidates_by_service(
                session=self.session,
                service_name=service_name,
                min_qualification_level=1
            )

        return candidates