from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import neo4j_service, postgres_service
from app.main import app

client = TestClient(app)


class FakeConnection:
    async def fetchval(self, _query):
        return 1


class FakeResult:
    def __init__(self, record):
        self.record = record

    async def single(self):
        return self.record


class FakeSession:
    def __init__(self, record):
        self.record = record

    async def run(self, _query, **_parameters):
        return FakeResult(self.record)


def test_liveness_does_not_require_databases() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_requires_fresh_nonempty_snapshot() -> None:
    version = uuid4()

    async def connection_dependency():
        yield FakeConnection()

    async def session_dependency():
        yield FakeSession(
            {
                "active_version": str(version),
                "node_count": 10,
                "snapshot_age_seconds": 30,
            }
        )

    previous_connection = app.dependency_overrides.get(postgres_service.get_connection)
    previous_session = app.dependency_overrides.get(neo4j_service.get_read_session)
    app.dependency_overrides[postgres_service.get_connection] = connection_dependency
    app.dependency_overrides[neo4j_service.get_read_session] = session_dependency
    try:
        response = client.get("/health/ready")
    finally:
        if previous_connection is None:
            app.dependency_overrides.pop(postgres_service.get_connection, None)
        else:
            app.dependency_overrides[postgres_service.get_connection] = (
                previous_connection
            )
        if previous_session is None:
            app.dependency_overrides.pop(neo4j_service.get_read_session, None)
        else:
            app.dependency_overrides[neo4j_service.get_read_session] = previous_session

    assert response.status_code == 200
    assert response.json()["active_sync_version"] == str(version)
    assert response.json()["snapshot_node_count"] == 10


def test_readiness_rejects_empty_snapshot() -> None:
    async def connection_dependency():
        yield FakeConnection()

    async def session_dependency():
        yield FakeSession(
            {
                "active_version": str(uuid4()),
                "node_count": 0,
                "snapshot_age_seconds": 30,
            }
        )

    previous_connection = app.dependency_overrides.get(postgres_service.get_connection)
    previous_session = app.dependency_overrides.get(neo4j_service.get_read_session)
    app.dependency_overrides[postgres_service.get_connection] = connection_dependency
    app.dependency_overrides[neo4j_service.get_read_session] = session_dependency
    try:
        response = client.get("/health/ready")
    finally:
        if previous_connection is None:
            app.dependency_overrides.pop(postgres_service.get_connection, None)
        else:
            app.dependency_overrides[postgres_service.get_connection] = (
                previous_connection
            )
        if previous_session is None:
            app.dependency_overrides.pop(neo4j_service.get_read_session, None)
        else:
            app.dependency_overrides[neo4j_service.get_read_session] = previous_session

    assert response.status_code == 503
