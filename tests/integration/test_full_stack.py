import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from tests.integration import graph_seed as seed
from tests.integration.conftest import (
    _point_neo4j_at_the_test_database,
    _point_postgres_at_the_test_database,
    admin_session,
    needs_neo4j,
    needs_postgres,
)

pytestmark = [needs_neo4j, needs_postgres]


@pytest.fixture
async def stack(monkeypatch, seeded_postgres, reset_graph_cooldown):
    _point_neo4j_at_the_test_database(monkeypatch)
    _point_postgres_at_the_test_database(monkeypatch)
    async with admin_session() as session:
        await seed.seed_graph(session)
    yield
    async with admin_session() as session:
        await seed.clear_graph(session)


def test_authenticated_feeds_are_served_from_the_graph(stack):
    with TestClient(app) as client:
        response = client.get("/feeds/offers", params={"strategy": "most_proven"})
        ready = client.get("/health/ready")

    body = response.json()
    assert response.status_code == 200
    assert body["source"] == "graph"
    assert body["context"]["sync_version"] == seed.VERSION
    assert [item["offer_id"] for item in body["items"]] == [seed.FAR_OFFER, seed.OFFER]
    assert ready.json()["graph"] == "ready"
    assert ready.json()["active_sync_version"] == seed.VERSION


def test_public_feeds_ignore_the_graph_and_use_sql(stack):
    with TestClient(app) as client:
        response = client.get("/public/feeds/suppliers")

    body = response.json()
    assert response.status_code == 200
    assert body["source"] == "fallback"
    assert [item["supplier_id"] for item in body["items"]] == ["00000000-0000-0000-0000-0000000000d1"]
    assert "public" in response.headers["cache-control"]


def test_feeds_switch_to_sql_when_the_graph_is_unreachable(stack, monkeypatch):
    monkeypatch.setattr(settings, "DB_NEO4J_URI", "bolt://127.0.0.1:1")
    monkeypatch.setattr(settings, "GRAPH_TIMEOUT_SECONDS", 1.0)

    with TestClient(app) as client:
        response = client.get("/feeds/professionals")
        ready = client.get("/health/ready")

    body = response.json()
    assert response.status_code == 200
    assert body["source"] == "fallback"
    assert body["context"]["sync_version"] is None
    assert [item["technician_id"] for item in body["items"]] == ["00000000-0000-0000-0000-000000000171"]
    assert ready.status_code == 200
    assert ready.json()["graph"] == "unavailable"


def test_the_service_runs_with_no_graph_configured_at_all(stack, monkeypatch):
    monkeypatch.setattr(settings, "DB_NEO4J_URI", None)

    with TestClient(app) as client:
        feed = client.get("/feeds/offers")
        ready = client.get("/health/ready")

    assert feed.json()["source"] == "fallback"
    assert ready.json()["graph"] == "disabled"
