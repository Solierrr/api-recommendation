import pytest

from app.errors import GraphUnavailableError, SnapshotUnavailableError
from tests.factories import VERSION
from tests.fakes import FakeGraph, FakePostgres, FakeResult


def healthy_graph() -> FakeGraph:
    return FakeGraph(
        handler=lambda query, parameters: FakeResult(
            single_return={"active_version": VERSION, "snapshot_age_seconds": 120}
        )
    )


def test_liveness_never_touches_the_dependencies(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_reports_a_healthy_graph(client, wired):
    wired[0].handler = healthy_graph().handler

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "postgres": "connected",
        "graph": "ready",
        "active_sync_version": VERSION,
        "snapshot_age_seconds": 120,
    }


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (SnapshotUnavailableError("sem snapshot"), "no_snapshot"),
        (GraphUnavailableError("fora do ar"), "unavailable"),
    ],
)
def test_readiness_stays_ready_when_the_graph_is_degraded(client, wired, error, expected):
    wired[0].error = error

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["graph"] == expected
    assert response.json()["active_sync_version"] is None


def test_readiness_reports_a_graph_that_is_not_configured(client, wired):
    wired[0].configured = False

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["graph"] == "disabled"


def test_readiness_fails_only_when_postgres_is_down(client, graph):
    from app.dependencies import get_graph, get_postgres
    from app.main import app

    app.dependency_overrides[get_graph] = lambda: graph
    app.dependency_overrides[get_postgres] = lambda: FakePostgres(error=OSError("recusou"))
    try:
        response = client.get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "recusou" not in response.text
