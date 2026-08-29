import os

# Garante que as configurações obrigatórias existam ANTES de qualquer import
# de módulos da aplicação (app.config instancia Settings() no import). Isso
# permite rodar a suíte de testes em ambientes sem um arquivo .env real
# (ex: CI), sem depender de credenciais verdadeiras do Neo4j.
os.environ.setdefault("NEO4J_URI", "neo4j://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "test-password")
os.environ.setdefault("API_KEY", "test-api-key")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import neo4j_service  # noqa: E402
from app.main import app  # noqa: E402

VALID_API_KEY = os.environ["API_KEY"]


@pytest.fixture
def client():
    """Cliente de teste síncrono para a API.

    Importante: instanciado sem `with`, para que o lifespan (que conectaria
    de fato ao Neo4j) não seja executado durante os testes unitários.
    """
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": VALID_API_KEY}


@pytest.fixture
def override_session():
    """Permite substituir a sessão do Neo4j injetada via Depends por um fake."""

    applied = []

    def _apply(fake_session):
        async def _get_session():
            yield fake_session

        app.dependency_overrides[neo4j_service.get_session] = _get_session
        applied.append(True)

    yield _apply

    if applied:
        app.dependency_overrides.pop(neo4j_service.get_session, None)
