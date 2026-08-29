from enum import StrEnum

from neo4j import AsyncSession


class EventLogResult(StrEnum):
    CREATED = "CREATED"
    SNAPSHOT_UNAVAILABLE = "SNAPSHOT_UNAVAILABLE"
    CANDIDATE_NOT_FOUND = "CANDIDATE_NOT_FOUND"


class EventRepository:
    SOURCE = "api-core"

    @staticmethod
    async def log_event(
        session: AsyncSession,
        user_id: str,
        candidate_id: str,
        event_type: str,
    ) -> EventLogResult:
        """Valida o snapshot e grava telemetria fora do ciclo de retenção versionado."""
        query = """
        OPTIONAL MATCH (state:SyncState {source: $source})
        WITH state.active_version AS active_version
        OPTIONAL MATCH (candidate:Technician {
            source: $source,
            sync_version: active_version,
            id: $candidate_id
        })
        WHERE candidate.user_active = true
        OPTIONAL MATCH (candidate)-[registration:REGISTERED_AS]->(profession:Profession {
            source: $source,
            sync_version: active_version
        })
        WHERE registration.source = $source
          AND registration.sync_version = active_version
        WITH active_version,
             candidate,
             count(profession) > 0 AS candidate_is_eligible
        FOREACH (_ IN CASE WHEN candidate_is_eligible THEN [1] ELSE [] END |
            MERGE (user:TelemetryUser {id: $user_id})
            CREATE (event:TelemetryEvent {
                event_id: randomUUID(),
                candidate_id: candidate.id,
                event_type: $event_type,
                occurred_at: datetime(),
                validated_sync_version: active_version
            })
            CREATE (user)-[:RECORDED]->(event)
        )
        RETURN CASE
            WHEN active_version IS NULL THEN 'SNAPSHOT_UNAVAILABLE'
            WHEN NOT candidate_is_eligible THEN 'CANDIDATE_NOT_FOUND'
            ELSE 'CREATED'
        END AS status
        """
        result = await session.run(
            query,
            source=EventRepository.SOURCE,
            candidate_id=candidate_id,
            user_id=user_id,
            event_type=event_type,
        )
        record = await result.single()
        if record is None:
            raise RuntimeError("A validação do evento não retornou um estado")

        try:
            return EventLogResult(record["status"])
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError("A validação do evento retornou um estado inválido") from error
