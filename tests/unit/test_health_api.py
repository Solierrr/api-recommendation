import asyncio

from app.version import VERSION
from tests.fakes import FakeGraph, FakePostgres


def override(postgres):
    from app.dependencies import get_graph, get_postgres
    from app.main import app

    app.dependency_overrides[get_graph] = lambda: FakeGraph(error=AssertionError("o pronto não usa o grafo"))
    app.dependency_overrides[get_postgres] = lambda: postgres
    return app


def test_health_never_touches_the_dependencies_and_reports_the_version(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "UP", "version": VERSION}


def test_ready_is_up_when_postgres_answers_whatever_the_graph_state(client):
    app = override(FakePostgres())
    try:
        response = client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_ready_is_down_without_details_when_postgres_fails(client):
    app = override(FakePostgres(error=OSError("recusou")))
    try:
        response = client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"status": "DOWN"}


def test_ready_gives_up_when_postgres_hangs(client, monkeypatch):
    from app import health

    async def hang(postgres):
        await asyncio.sleep(10)

    monkeypatch.setattr(health, "_ping", hang)
    monkeypatch.setattr(health, "READY_TIMEOUT_SECONDS", 0.01)
    app = override(FakePostgres())
    try:
        response = client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
