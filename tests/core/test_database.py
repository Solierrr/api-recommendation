import pytest

from app import database
from app.config import settings
from app.database import PostgresService


class FakeConnection:
    async def execute(self, _query):
        return None

    async def fetchval(self, _query):
        return 1


class AcquireContext:
    async def __aenter__(self):
        return FakeConnection()

    async def __aexit__(self, _exc_type, _exc, _traceback):
        return None


class FakePool:
    def acquire(self):
        return AcquireContext()


@pytest.mark.asyncio
async def test_postgres_preserves_configured_sslmode(monkeypatch) -> None:
    captured = {}

    async def create_pool(**kwargs):
        captured.update(kwargs)
        return FakePool()

    monkeypatch.setattr(settings, "DB_POSTGRES_SSLMODE", "verify-full")
    monkeypatch.setattr(database.asyncpg, "create_pool", create_pool)

    await PostgresService().connect()

    assert captured["ssl"] == "verify-full"
