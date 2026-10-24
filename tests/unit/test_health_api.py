import pytest

from app.errors import GraphUnavailableError, SnapshotUnavailableError
from tests.factories import VERSION
from tests.fakes import FakeGraph, FakeResult


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
    wired.handler = healthy_graph().handler

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
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
def test_readiness_reports_a_degraded_graph_without_failing(client, wired, error, expected):
    wired.error = error

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["graph"] == expected
    assert response.json()["active_sync_version"] is None


def test_readiness_reports_a_graph_that_is_not_configured(client, wired):
    wired.configured = False

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["graph"] == "disabled"
