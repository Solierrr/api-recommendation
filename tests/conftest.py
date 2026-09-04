import os

# Configura o processo de testes antes de importar app.config, sem depender do
# .env local ou de credenciais reais.
os.environ["APP_ENVIRONMENT"] = "test"
os.environ["APP_TIMEZONE"] = "America/Sao_Paulo"
os.environ["DOCS_ENABLED"] = "true"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "test-password"
os.environ.pop("NEO4J_DATABASE", None)
os.environ["DB_POSTGRES_HOST"] = "localhost"
os.environ["DB_POSTGRES_PORT"] = "5432"
os.environ["DB_POSTGRES_CORE"] = "test"
os.environ["DB_POSTGRES_USER"] = "test"
os.environ["DB_POSTGRES_PASSWORD"] = "test-password"
os.environ["DB_POSTGRES_SSLMODE"] = "disable"
os.environ["API_KEY"] = "test-api-key"
os.environ["SYNC_API_KEY"] = "test-sync-key-with-at-least-32-characters"
os.environ.pop("RECOMMENDATION_API_KEY", None)
os.environ["SYNC_ON_STARTUP"] = "false"
os.environ["SYNC_BATCH_SIZE"] = "500"
os.environ["SYNC_LOCK_LEASE_SECONDS"] = "900"
os.environ["SYNC_MIN_DOMAIN_RETENTION_RATIO"] = "0.5"
os.environ["SNAPSHOT_MAX_AGE_SECONDS"] = "86400"
os.environ["RECOMMENDATION_RESULT_LIMIT"] = "10"
os.environ["RECOMMENDATION_POOL_LIMIT"] = "500"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api import health as health_api  # noqa: E402
from app.database import neo4j_service  # noqa: E402
from app.main import app  # noqa: E402

VALID_API_KEY = os.environ["API_KEY"]


@pytest.fixture
def client():
    # Sem context manager: os testes de API não executam o lifespan real.
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": VALID_API_KEY}


@pytest.fixture
def override_session():
    """Substitui todas as dependências Neo4j usadas pelas rotas públicas."""

    dependencies = (
        neo4j_service.get_session,
        neo4j_service.get_read_session,
        neo4j_service.get_write_session,
    )

    def _apply(fake_session):
        async def _get_session():
            yield fake_session

        for dependency in dependencies:
            app.dependency_overrides[dependency] = _get_session

    yield _apply

    for dependency in dependencies:
        app.dependency_overrides.pop(dependency, None)


@pytest.fixture
def override_health():
    """Substitui PostgreSQL e Neo4j utilizados pelos endpoints de readiness."""

    dependencies = (health_api.get_health_connection, health_api.get_health_session)

    def _apply(fake_connection, fake_session):
        async def _get_connection():
            yield fake_connection

        async def _get_session():
            yield fake_session

        app.dependency_overrides[health_api.get_health_connection] = _get_connection
        app.dependency_overrides[health_api.get_health_session] = _get_session

    yield _apply

    for dependency in dependencies:
        app.dependency_overrides.pop(dependency, None)
