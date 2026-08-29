import asyncio
import os
from uuid import uuid4

import pytest
from neo4j import AsyncGraphDatabase

from app.core.errors import SyncInProgressError
from app.repositories.core_graph_repository import CoreGraphSnapshot
from app.repositories.graph_sync_repository import GraphSyncRepository

INTEGRATION_URI = os.getenv("NEO4J_INTEGRATION_URI")
DESTRUCTIVE_OPT_IN = (
    os.getenv("NEO4J_INTEGRATION_ALLOW_DESTRUCTIVE", "").lower() == "true"
)
pytestmark = pytest.mark.skipif(
    not INTEGRATION_URI or not DESTRUCTIVE_OPT_IN,
    reason=("NEO4J_INTEGRATION_URI e opt-in destrutivo explícito não configurados"),
)


def snapshot(unit_count: int) -> CoreGraphSnapshot:
    return CoreGraphSnapshot(
        local_units=[
            {
                "id": f"unit-{index}",
                "location_type": "HOUSE",
                "complement": None,
                "geolocation_count": 0,
                "latitude": None,
                "longitude": None,
            }
            for index in range(unit_count)
        ],
        panel_offers=[],
        professions=[],
        professionals=[],
        affiliations=[],
        shifts=[],
        technical_services=[],
        service_experiences=[],
        assignments=[],
    )


async def connected_driver():
    driver = AsyncGraphDatabase.driver(
        INTEGRATION_URI,
        auth=(
            os.getenv("NEO4J_INTEGRATION_USER", "neo4j"),
            os.getenv("NEO4J_INTEGRATION_PASSWORD", "test-password-for-ci"),
        ),
    )
    last_error = None
    for _ in range(30):
        try:
            await driver.verify_connectivity()
            return driver
        except Exception as error:
            last_error = error
            await asyncio.sleep(2)
    await driver.close()
    raise RuntimeError("Neo4j de integração não ficou disponível") from last_error


@pytest.mark.asyncio
async def test_real_neo4j_lock_activation_validation_and_cleanup(monkeypatch) -> None:
    integration_source = f"api-recommendation-integration-{uuid4()}"
    monkeypatch.setattr(GraphSyncRepository, "SOURCE", integration_source)
    driver = await connected_driver()
    try:
        async with driver.session() as session:
            await GraphSyncRepository.stage_and_activate(
                session,
                snapshot(1),
                "version-1",
            )
            await GraphSyncRepository.stage_and_activate(
                session,
                snapshot(2),
                "version-2",
            )
            await GraphSyncRepository.stage_and_activate(
                session,
                snapshot(2),
                "version-3",
            )

            state = await (
                await session.run(
                    """
                    MATCH (state:SyncState {source: $source})
                    RETURN state.active_version AS active_version,
                           state.previous_version AS previous_version
                    """,
                    source=GraphSyncRepository.SOURCE,
                )
            ).single()
            assert state["active_version"] == "version-3"
            assert state["previous_version"] == "version-2"

            result = await session.run(
                """
                MATCH (node)
                WHERE node.source = $source
                  AND node.sync_version IS NOT NULL
                RETURN node.sync_version AS version, count(node) AS node_count
                ORDER BY version
                """,
                source=GraphSyncRepository.SOURCE,
            )
            versions = {
                record["version"]: record["node_count"] async for record in result
            }
            assert versions == {"version-2": 2, "version-3": 2}

            await GraphSyncRepository.begin_sync(session, "lock-holder")
            with pytest.raises(SyncInProgressError):
                await GraphSyncRepository.begin_sync(session, "blocked-sync")
            await GraphSyncRepository.abort_sync(session, "lock-holder")

            async def concurrent_acquire(version: str):
                async with driver.session() as contender_session:
                    try:
                        await GraphSyncRepository.begin_sync(
                            contender_session,
                            version,
                        )
                    except SyncInProgressError as error:
                        return error
                    return version

            contenders = await asyncio.gather(
                concurrent_acquire("concurrent-a"),
                concurrent_acquire("concurrent-b"),
            )
            winners = [result for result in contenders if isinstance(result, str)]
            blocked = [
                result
                for result in contenders
                if isinstance(result, SyncInProgressError)
            ]
            assert len(winners) == len(blocked) == 1
            await GraphSyncRepository.abort_sync(session, winners[0])

            await (
                await session.run(
                    """
                    CREATE (:LocalUnit {
                        source: $source,
                        sync_version: 'orphan-version',
                        graph_key: $source + '|orphan-version|unit'
                    })
                    """,
                    source=GraphSyncRepository.SOURCE,
                )
            ).consume()
            await GraphSyncRepository.begin_sync(session, "orphan-reaper")
            orphan_record = await (
                await session.run(
                    """
                    MATCH (node {source: $source, sync_version: 'orphan-version'})
                    RETURN count(node) AS node_count
                    """,
                    source=GraphSyncRepository.SOURCE,
                )
            ).single()
            assert orphan_record["node_count"] == 0
            await GraphSyncRepository.abort_sync(session, "orphan-reaper")
    finally:
        async with driver.session() as cleanup_session:
            await (
                await cleanup_session.run(
                    """
                    MATCH (node {source: $source})
                    DETACH DELETE node
                    """,
                    source=integration_source,
                )
            ).consume()
        await driver.close()
