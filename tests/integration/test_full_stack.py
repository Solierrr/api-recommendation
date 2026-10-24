import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from tests.integration import graph_seed as seed
from tests.integration.conftest import _point_neo4j_at_the_test_database, admin_session, needs_neo4j

pytestmark = needs_neo4j


@pytest.fixture
async def stack(monkeypatch, reset_graph_cooldown):
    _point_neo4j_at_the_test_database(monkeypatch)
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


def test_public_feeds_are_served_from_the_graph(stack):
    with TestClient(app) as client:
        response = client.get("/public/feeds/suppliers")

    body = response.json()
    assert response.status_code == 200
    assert body["source"] == "graph"
    assert {item["supplier_id"] for item in body["items"]} == {seed.FAR_SUPPLIER, seed.SUPPLIER}
    assert "public" in response.headers["cache-control"]


def test_feeds_answer_503_when_the_graph_is_unreachable(stack, monkeypatch):
    monkeypatch.setattr(settings, "DB_NEO4J_URI", "bolt://127.0.0.1:1")
    monkeypatch.setattr(settings, "GRAPH_TIMEOUT_SECONDS", 1.0)

    with TestClient(app) as client:
        response = client.get("/feeds/professionals")
        ready = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "FEED_UNAVAILABLE"
    assert ready.status_code == 200
    assert ready.json()["graph"] == "unavailable"


def test_feeds_answer_503_when_no_graph_is_configured(stack, monkeypatch):
    monkeypatch.setattr(settings, "DB_NEO4J_URI", None)

    with TestClient(app) as client:
        feed = client.get("/feeds/offers")
        ready = client.get("/health/ready")

    assert feed.status_code == 503
    assert feed.json()["detail"]["code"] == "FEED_UNAVAILABLE"
    assert ready.json()["graph"] == "disabled"
