import logging
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import settings


@pytest.fixture
def graph(monkeypatch):
    graph = AsyncMock()
    monkeypatch.setattr(main, "graph_service", graph)
    return graph


def test_startup_connects_the_graph_and_closes_it(graph):
    with TestClient(main.app):
        graph.connect.assert_awaited_once()

    graph.close.assert_awaited_once()


def test_startup_refuses_an_insecure_production_configuration(graph, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENVIRONMENT", "production")

    with pytest.raises(RuntimeError), TestClient(main.app):
        pass

    graph.connect.assert_not_awaited()


def test_driver_schema_notifications_do_not_flood_the_logs():
    assert logging.getLogger("neo4j.notifications").level == logging.ERROR
