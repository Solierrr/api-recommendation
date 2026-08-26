from neo4j import AsyncSession


class EventRepository:
    @staticmethod
    async def log_event(
        session: AsyncSession, user_id: str, candidate_id: str, event_type: str
    ) -> bool:
        """Cria uma aresta de interação entre o usuário e o profissional no grafo.

        Retorna False quando o candidato informado não existe no grafo, evitando
        a criação de eventos "órfãos" apontando para profissionais inexistentes.
        """
        query = """
        MATCH (p:Profissional {id: $candidate_id})
        MERGE (u:Usuario {id: $user_id})
        CREATE (u)-[r:INTERAGIU {tipo: $event_type, timestamp: datetime()}]->(p)
        RETURN r
        """
        result = await session.run(
            query, candidate_id=candidate_id, user_id=user_id, event_type=event_type
        )
        record = await result.single()
        return record is not None
