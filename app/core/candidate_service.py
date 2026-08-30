from neo4j import AsyncSession

from app.repositories.candidate_repository import CandidateRepository


class CandidateService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_candidate_pool(
        self,
        service_name: str,
        min_rating: float = 0,
    ) -> list[dict]:
        """Busca candidatos respeitando estritamente a nota mínima informada."""
        return await CandidateRepository.find_candidates_by_service(
            session=self.session,
            service_name=service_name,
            min_rating=min_rating,
        )
