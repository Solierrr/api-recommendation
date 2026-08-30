from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_lifespan_connects_and_closes_both_databases(monkeypatch):
    monkeypatch.setattr(settings, "SYNC_ON_STARTUP", False)

    with (
        patch("app.main.postgres_service.connect", new=AsyncMock()) as postgres_connect,
        patch("app.main.postgres_service.close", new=AsyncMock()) as postgres_close,
        patch("app.main.neo4j_service.connect", new=AsyncMock()) as neo4j_connect,
        patch("app.main.neo4j_service.close", new=AsyncMock()) as neo4j_close,
    ):
        with TestClient(app) as client:
            postgres_connect.assert_awaited_once()
            neo4j_connect.assert_awaited_once()
            postgres_close.assert_not_awaited()
            neo4j_close.assert_not_awaited()
            assert client.app is app

        neo4j_close.assert_awaited_once()
        postgres_close.assert_awaited_once()
