from unittest.mock import AsyncMock, patch

import pytest
from neo4j import READ_ACCESS, WRITE_ACCESS

from app.config import settings
from app.database import Neo4jService


@pytest.mark.asyncio
async def test_connect_initializes_driver_and_verifies_connectivity():
    service = Neo4jService()
    fake_driver = AsyncMock()

    with patch(
        "app.database.AsyncGraphDatabase.driver",
        return_value=fake_driver,
    ) as mocked_driver_factory:
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
    assert service._driver is None


@pytest.mark.asyncio
async def test_close_is_noop_when_driver_not_initialized():
    await Neo4jService().close()


@pytest.mark.asyncio
async def test_get_session_raises_when_driver_not_initialized():
    service = Neo4jService()

    with pytest.raises(RuntimeError, match="Driver Neo4j não foi inicializado"):
        async for _ in service.get_session():
            pass


class FakeSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_exc_info):
        return None


@pytest.mark.asyncio
async def test_get_session_yields_read_session_with_database():
    service = Neo4jService()
    fake_session = AsyncMock()
    captured = {}

    def session_factory(**kwargs):
        captured.update(kwargs)
        return FakeSessionContext(fake_session)

    fake_driver = AsyncMock()
    fake_driver.session = session_factory
    service._driver = fake_driver

    sessions = [session async for session in service.get_session()]

    assert sessions == [fake_session]
    assert captured == {
        "database": settings.NEO4J_DATABASE,
        "default_access_mode": READ_ACCESS,
    }


@pytest.mark.asyncio
async def test_get_write_session_uses_write_access():
    service = Neo4jService()
    captured = {}

    def session_factory(**kwargs):
        captured.update(kwargs)
        return FakeSessionContext(AsyncMock())

    fake_driver = AsyncMock()
    fake_driver.session = session_factory
    service._driver = fake_driver

    sessions = [session async for session in service.get_write_session()]

    assert len(sessions) == 1
    assert captured["default_access_mode"] == WRITE_ACCESS
