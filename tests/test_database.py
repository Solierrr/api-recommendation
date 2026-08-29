from unittest.mock import AsyncMock, patch

import pytest

from app.database import Neo4jService


@pytest.mark.asyncio
async def test_connect_initializes_driver_and_verifies_connectivity():
    service = Neo4jService()
    fake_driver = AsyncMock()

    with patch("app.database.AsyncGraphDatabase.driver", return_value=fake_driver) as mocked_driver_factory:
        await service.connect()

    mocked_driver_factory.assert_called_once()
    fake_driver.verify_connectivity.assert_awaited_once()
    assert service._driver is fake_driver


@pytest.mark.asyncio
async def test_close_closes_driver_when_initialized():
    service = Neo4jService()
    fake_driver = AsyncMock()
    service._driver = fake_driver

    await service.close()

    fake_driver.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_is_noop_when_driver_not_initialized():
    service = Neo4jService()

    # Não deve lançar exceção mesmo sem um driver inicializado.
    await service.close()


@pytest.mark.asyncio
async def test_get_session_raises_when_driver_not_initialized():
    service = Neo4jService()

    with pytest.raises(RuntimeError, match="Driver Neo4j não foi inicializado"):
        async for _ in service.get_session():
            pass


@pytest.mark.asyncio
async def test_get_session_yields_session_from_driver():
    service = Neo4jService()
    fake_session = AsyncMock()

    class _FakeContextManager:
        async def __aenter__(self):
            return fake_session

        async def __aexit__(self, *exc_info):
            return None

    fake_driver = AsyncMock()
    fake_driver.session = lambda: _FakeContextManager()
    service._driver = fake_driver

    sessions = [s async for s in service.get_session()]

    assert sessions == [fake_session]
