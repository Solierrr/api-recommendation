from contextlib import asynccontextmanager

import pytest
from neo4j.exceptions import ServiceUnavailable
from pydantic import SecretStr

import app.database as database
from app.config import settings
from app.database import GraphService, PostgresService
from app.errors import GraphUnavailableError


class FakeNeo4jSession:
    pass


class FakeDriver:
    def __init__(self, verify_error: Exception | None = None):
        self.verify_error = verify_error
        self.closed = False
        self.session_arguments: dict | None = None

    async def verify_connectivity(self) -> None:
        if self.verify_error:
            raise self.verify_error

    def session(self, **arguments):
        self.session_arguments = arguments

        @asynccontextmanager
        async def manager():
            yield FakeNeo4jSession()

        return manager()

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(settings, "DB_NEO4J_URI", "bolt://feeddb:7687")
    monkeypatch.setattr(settings, "DB_NEO4J_PASSWORD", SecretStr("senha"))
    monkeypatch.setattr(settings, "DB_NEO4J_FEED", "feeddb")
    monkeypatch.setattr(settings, "GRAPH_RETRY_AFTER_SECONDS", 30)


def use_driver(monkeypatch, driver: FakeDriver) -> dict:
    captured: dict = {}

    def create(uri, **arguments):
        captured["uri"] = uri
        captured.update(arguments)
        return driver

    monkeypatch.setattr(database.AsyncGraphDatabase, "driver", create)
    return captured


async def test_graph_without_configuration_is_never_available():
    graph = GraphService()

    await graph.connect()

    assert not graph.configured
    assert not graph.available
    with pytest.raises(GraphUnavailableError):
        async with graph.read_session():
            pass


async def test_graph_connects_with_the_configured_database(configured, monkeypatch):
    driver = FakeDriver()
    captured = use_driver(monkeypatch, driver)
    graph = GraphService()

    await graph.connect()

    assert graph.available
    assert captured["uri"] == "bolt://feeddb:7687"
    assert captured["auth"] == ("neo4j", "senha")
    async with graph.read_session() as session:
        assert isinstance(session, FakeNeo4jSession)
    assert driver.session_arguments["database"] == "feeddb"


async def test_graph_keeps_the_driver_when_it_is_down_at_startup(configured, monkeypatch):
    driver = FakeDriver(verify_error=ServiceUnavailable("fora"))
    use_driver(monkeypatch, driver)
    graph = GraphService()

    await graph.connect()

    assert not graph.available
    with pytest.raises(GraphUnavailableError):
        async with graph.read_session():
            pass


async def test_graph_failures_start_a_cooldown_and_recover_afterwards(configured, monkeypatch):
    use_driver(monkeypatch, FakeDriver())
    graph = GraphService()
    await graph.connect()

    with pytest.raises(GraphUnavailableError):
        async with graph.read_session():
            raise ServiceUnavailable("caiu no meio da consulta")

    assert not graph.available
    with pytest.raises(GraphUnavailableError, match="espera"):
        async with graph.read_session():
            raise AssertionError("não deveria abrir sessão durante a espera")

    graph._retry_at = 0.0
    assert graph.available


async def test_errors_that_are_not_connectivity_failures_pass_through(configured, monkeypatch):
    use_driver(monkeypatch, FakeDriver())
    graph = GraphService()
    await graph.connect()

    with pytest.raises(ValueError, match="bug"):
        async with graph.read_session():
            raise ValueError("bug")

    assert graph.available


async def test_graph_close_releases_the_driver(configured, monkeypatch):
    driver = FakeDriver()
    use_driver(monkeypatch, driver)
    graph = GraphService()
    await graph.connect()

    await graph.close()

    assert driver.closed
    assert not graph.available


class FakeTransaction:
    def __init__(self, readonly: bool):
        self.readonly = readonly

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exception):
        return False


class FakeConnection:
    def __init__(self):
        self.statements: list[str] = []

    async def execute(self, statement: str) -> None:
        self.statements.append(statement)

    async def fetchval(self, statement: str) -> int:
        self.statements.append(statement)
        return 1

    def transaction(self, readonly: bool):
        return FakeTransaction(readonly)


class FakePool:
    def __init__(self):
        self.connection = FakeConnection()
        self.closed = False

    @asynccontextmanager
    async def acquire(self):
        yield self.connection

    async def close(self) -> None:
        self.closed = True


async def test_postgres_connects_read_only_and_exposes_read_only_connections(monkeypatch):
    pool = FakePool()
    captured: dict = {}

    async def create_pool(**arguments):
        captured.update(arguments)
        return pool

    monkeypatch.setattr(database.asyncpg, "create_pool", create_pool)
    service = PostgresService()

    await service.connect()

    assert "SET default_transaction_read_only = on" in pool.connection.statements
    assert captured["server_settings"]["application_name"] == "api-recommendation"
    async with service.connection() as connection:
        assert connection is pool.connection
    await service.close()
    assert pool.closed


async def test_postgres_connection_requires_an_initialized_pool():
    with pytest.raises(RuntimeError, match="Pool"):
        async with PostgresService().connection():
            pass
