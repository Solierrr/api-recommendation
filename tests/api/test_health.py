from app.api import health as health_api
from tests.fakes import FakeConnection, FakeResult, FakeSession


class TrackedAsyncContext:
    def __init__(
        self,
        value,
        events,
        label,
        *,
        enter_error=None,
        exit_error=None,
    ):
        self.value = value
        self.events = events
        self.label = label
        self.enter_error = enter_error
        self.exit_error = exit_error

    async def __aenter__(self):
        self.events.append(f"{self.label}:enter")
        if self.enter_error is not None:
            raise self.enter_error
        return self.value

    async def __aexit__(self, *_exc_info):
        self.events.append(f"{self.label}:exit")
        if self.exit_error is not None:
            raise self.exit_error
        return None


def ready_record(**overrides):
    record = {
        "active_version": "00000000-0000-0000-0000-000000000001",
        "node_count": 10,
        "snapshot_age_seconds": 30,
    }
    record.update(overrides)
    return record


def test_liveness_is_public_and_does_not_require_databases(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_health_check_is_public_and_returns_200_when_ready(client, override_health):
    connection = FakeConnection()
    session = FakeSession(result=FakeResult(single_return=ready_record()))
    override_health(connection, session)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "online",
        "postgres": "connected",
        "neo4j": "connected",
    }


def test_readiness_returns_fresh_snapshot_metadata(client, override_health):
    override_health(
        FakeConnection(),
        FakeSession(result=FakeResult(single_return=ready_record())),
    )

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["active_sync_version"] == ready_record()["active_version"]
    assert response.json()["snapshot_node_count"] == 10


def test_health_check_returns_503_when_neo4j_query_fails(client, override_health):
    def _raise(_query, _params):
        raise RuntimeError("connection refused")

    override_health(FakeConnection(), FakeSession(result_factory=_raise))

    response = client.get("/health")

    assert response.status_code == 503
    assert "connection refused" not in response.text


def test_health_check_returns_503_when_postgres_is_unavailable(client, override_health):
    override_health(
        FakeConnection(fetchval_return=0),
        FakeSession(result=FakeResult(single_return=ready_record())),
    )

    response = client.get("/health")

    assert response.status_code == 503


def test_readiness_rejects_empty_snapshot(client, override_health):
    override_health(
        FakeConnection(),
        FakeSession(result=FakeResult(single_return=ready_record(node_count=0))),
    )

    response = client.get("/health/ready")

    assert response.status_code == 503


def test_readiness_releases_dependencies_before_success_response(client, monkeypatch):
    events = []
    connection = FakeConnection()
    session = FakeSession(result=FakeResult(single_return=ready_record()))
    monkeypatch.setattr(
        health_api.postgres_service,
        "connection",
        lambda: TrackedAsyncContext(connection, events, "postgres"),
    )
    monkeypatch.setattr(
        health_api.neo4j_service,
        "read_session",
        lambda: TrackedAsyncContext(session, events, "neo4j"),
    )

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert events == ["postgres:enter", "neo4j:enter", "neo4j:exit", "postgres:exit"]


def test_readiness_sanitizes_postgres_acquisition_failure(client, monkeypatch):
    events = []
    secret = "postgres acquisition secret"
    monkeypatch.setattr(
        health_api.postgres_service,
        "connection",
        lambda: TrackedAsyncContext(
            FakeConnection(),
            events,
            "postgres",
            enter_error=RuntimeError(secret),
        ),
    )
    monkeypatch.setattr(
        health_api.neo4j_service,
        "read_session",
        lambda: TrackedAsyncContext(FakeSession(), events, "neo4j"),
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert secret not in response.text
    assert events == ["postgres:enter"]


def test_readiness_releases_postgres_when_neo4j_acquisition_fails(client, monkeypatch):
    events = []
    secret = "neo4j acquisition secret"
    monkeypatch.setattr(
        health_api.postgres_service,
        "connection",
        lambda: TrackedAsyncContext(FakeConnection(), events, "postgres"),
    )
    monkeypatch.setattr(
        health_api.neo4j_service,
        "read_session",
        lambda: TrackedAsyncContext(
            FakeSession(),
            events,
            "neo4j",
            enter_error=RuntimeError(secret),
        ),
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert secret not in response.text
    assert events == ["postgres:enter", "neo4j:enter", "postgres:exit"]


def test_readiness_sanitizes_teardown_failure_before_response(client, monkeypatch):
    events = []
    secret = "postgres teardown secret"
    connection = FakeConnection()
    session = FakeSession(result=FakeResult(single_return=ready_record()))
    monkeypatch.setattr(
        health_api.postgres_service,
        "connection",
        lambda: TrackedAsyncContext(
            connection,
            events,
            "postgres",
            exit_error=RuntimeError(secret),
        ),
    )
    monkeypatch.setattr(
        health_api.neo4j_service,
        "read_session",
        lambda: TrackedAsyncContext(session, events, "neo4j"),
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert secret not in response.text
    assert events == ["postgres:enter", "neo4j:enter", "neo4j:exit", "postgres:exit"]
