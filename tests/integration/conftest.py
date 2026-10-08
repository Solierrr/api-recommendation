import os
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
import pytest
from neo4j import AsyncGraphDatabase
from pydantic import SecretStr

from app.config import settings
from app.database import GraphService, PostgresService, graph_service
from tests.integration.graph_seed import clear_graph, seed_graph

SEED_SQL = Path(__file__).parent / "fixtures" / "seed.sql"

ALLOWED = os.getenv("INTEGRATION_ALLOW_DESTRUCTIVE", "").lower() == "true"
NEO4J_URI = os.getenv("NEO4J_INTEGRATION_URI")
POSTGRES_HOST = os.getenv("POSTGRES_INTEGRATION_HOST")

needs_neo4j = pytest.mark.skipif(
    not (NEO4J_URI and ALLOWED),
    reason="NEO4J_INTEGRATION_URI e INTEGRATION_ALLOW_DESTRUCTIVE=true não configurados",
)
needs_postgres = pytest.mark.skipif(
    not (POSTGRES_HOST and ALLOWED),
    reason="POSTGRES_INTEGRATION_HOST e INTEGRATION_ALLOW_DESTRUCTIVE=true não configurados",
)


def _point_neo4j_at_the_test_database(monkeypatch) -> None:
    monkeypatch.setattr(settings, "DB_NEO4J_URI", NEO4J_URI)
    monkeypatch.setattr(settings, "DB_NEO4J_USER", os.getenv("NEO4J_INTEGRATION_USER", "neo4j"))
    monkeypatch.setattr(
        settings,
        "DB_NEO4J_PASSWORD",
        SecretStr(os.getenv("NEO4J_INTEGRATION_PASSWORD", "test-password-for-ci")),
    )
    monkeypatch.setattr(settings, "DB_NEO4J_FEED", os.getenv("NEO4J_INTEGRATION_DATABASE", "feeddb"))


def _point_postgres_at_the_test_database(monkeypatch) -> None:
    monkeypatch.setattr(settings, "DB_POSTGRES_HOST", POSTGRES_HOST)
    monkeypatch.setattr(settings, "DB_POSTGRES_PORT", int(os.getenv("POSTGRES_INTEGRATION_PORT", "5432")))
    monkeypatch.setattr(settings, "DB_POSTGRES_CORE", os.getenv("POSTGRES_INTEGRATION_DATABASE", "coredb"))
    monkeypatch.setattr(settings, "DB_POSTGRES_USER", os.getenv("POSTGRES_INTEGRATION_USER", "postgres"))
    monkeypatch.setattr(
        settings,
        "DB_POSTGRES_PASSWORD",
        SecretStr(os.getenv("POSTGRES_INTEGRATION_PASSWORD", "test-password-for-ci")),
    )


@asynccontextmanager
async def admin_session():
    driver = AsyncGraphDatabase.driver(
        NEO4J_URI,
        auth=(
            os.getenv("NEO4J_INTEGRATION_USER", "neo4j"),
            os.getenv("NEO4J_INTEGRATION_PASSWORD", "test-password-for-ci"),
        ),
    )
    try:
        async with driver.session(database=os.getenv("NEO4J_INTEGRATION_DATABASE", "feeddb")) as session:
            yield session
    finally:
        await driver.close()


@pytest.fixture
async def seeded_graph(monkeypatch):
    _point_neo4j_at_the_test_database(monkeypatch)
    async with admin_session() as session:
        await seed_graph(session)
    service = GraphService()
    await service.connect()
    assert service.available, "Neo4j de integração indisponível"
    yield service
    await service.close()
    async with admin_session() as session:
        await clear_graph(session)


@pytest.fixture
async def empty_graph(monkeypatch):
    _point_neo4j_at_the_test_database(monkeypatch)
    async with admin_session() as session:
        await clear_graph(session)
    service = GraphService()
    await service.connect()
    assert service.available, "Neo4j de integração indisponível"
    yield service
    await service.close()


@pytest.fixture
async def seeded_postgres(monkeypatch):
    _point_postgres_at_the_test_database(monkeypatch)
    connection = await asyncpg.connect(
        host=settings.DB_POSTGRES_HOST,
        port=settings.DB_POSTGRES_PORT,
        database=settings.DB_POSTGRES_CORE,
        user=settings.DB_POSTGRES_USER,
        password=settings.DB_POSTGRES_PASSWORD.get_secret_value(),
    )
    try:
        await connection.execute(SEED_SQL.read_text(encoding="utf-8"))
    finally:
        await connection.close()
    service = PostgresService()
    await service.connect()
    yield service
    await service.close()


@pytest.fixture
def reset_graph_cooldown():
    graph_service._retry_at = 0.0
    yield
    graph_service._retry_at = 0.0
