from neo4j import AsyncSession

class CandidateRepository:
    @staticmethod
    async def find_candidates_by_service(
        session: AsyncSession, 
        service_name: str, 
        min_qualification_level: int = 1
    ) -> list[dict]:
        """
        Executa a busca por travessia no grafo com pré-filtragem rígida.
        """
        query = """
        MATCH (p:Profissional)-[:OFERECE_SERVICO]->(s:Servico {nome: $service_name})
        MATCH (p)-[r:POSSUI_QUALIFICACAO]->(q:Qualificacao)
        WHERE r.nivel >= $min_level
        RETURN 
            p.id AS candidate_id,
            p.nome AS name,
            s.nome AS service,
            collect(q.nome) AS qualifications,
            avg(r.nivel) AS avg_qualification_score
        LIMIT 50
        """
        result = await session.run(
            query, 
            service_name=service_name, 
            min_level=min_qualification_level
        )
        return await result.data()