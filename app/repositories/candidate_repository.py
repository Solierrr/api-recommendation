from neo4j import AsyncSession


class CandidateRepository:
    SOURCE = "api-core"

    @staticmethod
    async def find_candidates_by_service(
        session: AsyncSession,
        service_name: str,
        min_rating: float = 0,
        limit: int = 50,
    ) -> list[dict]:
        query = """
        MATCH (state:SyncState {source: $source})
        MATCH (professional:Technician {
            source: $source,
            sync_version: state.active_version
        })-[registration:REGISTERED_AS]->(service:Profession {
            source: $source,
            sync_version: state.active_version
        })
        WHERE toLower(service.name) = toLower($service_name)
          AND coalesce(professional.average_rating_global, 0.0) >= $min_rating
        RETURN
            professional.id AS candidate_id,
            professional.name AS name,
            service.name AS service,
            coalesce(registration.certification_names, []) AS qualifications,
            coalesce(professional.average_rating_global, 0.0) AS average_rating,
            coalesce(professional.review_count_global, 0) AS review_count
        ORDER BY average_rating DESC, review_count DESC, name ASC
        LIMIT $limit
        """
        result = await session.run(
            query,
            source=CandidateRepository.SOURCE,
            service_name=service_name,
            min_rating=min_rating,
            limit=limit,
        )
        return await result.data()
