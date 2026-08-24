from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_lifespan_connects_and_closes_neo4j_service():
    with (
        patch("app.main.neo4j_service.connect", new=AsyncMock()) as mocked_connect,
        patch("app.main.neo4j_service.close", new=AsyncMock()) as mocked_close,
    ):
        with TestClient(app) as client:
            # Dentro do bloco `with`, o lifespan já rodou o startup.
            mocked_connect.assert_awaited_once()
            mocked_close.assert_not_awaited()
            assert client.app is app

        # Ao saír do bloco `with`, o shutdown do lifespan é executado.
        mocked_close.assert_awaited_once()
