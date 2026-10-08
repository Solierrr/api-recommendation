import logging
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import settings


@pytest.fixture
def services(monkeypatch):
    postgres = AsyncMock()
    graph = AsyncMock()
    monkeypatch.setattr(main, "postgres_service", postgres)
    monkeypatch.setattr(main, "graph_service", graph)
    return postgres, graph


def test_startup_connects_postgres_and_the_graph_and_closes_both(services):
    postgres, graph = services

    with TestClient(main.app):
        postgres.connect.assert_awaited_once()
        graph.connect.assert_awaited_once()

    graph.close.assert_awaited_once()
    postgres.close.assert_awaited_once()


def test_startup_fails_fast_when_postgres_is_unavailable(services):
    postgres, graph = services
    postgres.connect.side_effect = OSError("sem rota para o banco")

    with pytest.raises(OSError), TestClient(main.app):
        pass

    graph.connect.assert_not_awaited()
    postgres.close.assert_awaited_once()


def test_startup_refuses_an_insecure_production_configuration(services, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENVIRONMENT", "production")

    with pytest.raises(RuntimeError), TestClient(main.app):
        pass

    services[0].connect.assert_not_awaited()


def test_driver_schema_notifications_do_not_flood_the_logs():
    assert logging.getLogger("neo4j.notifications").level == logging.ERROR
