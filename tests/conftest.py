import os

# Configura o processo de testes antes de importar app.config, sem depender do
# .env local ou de credenciais reais.
os.environ["APP_ENVIRONMENT"] = "test"
os.environ["DOCS_ENABLED"] = "true"
for name in ("DB_NEO4J_URI", "DB_NEO4J_PASSWORD", "DB_NEO4J_FEED", "RECOMMENDATION_API_KEY"):
    os.environ.pop(name, None)
os.environ["RECOMMENDATION_RESULT_LIMIT"] = "10"
os.environ["RECOMMENDATION_POOL_LIMIT"] = "500"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.dependencies import get_graph  # noqa: E402
from app.main import app  # noqa: E402
from tests.fakes import FakeGraph  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def graph():
    return FakeGraph()


@pytest.fixture
def wired(graph):
    app.dependency_overrides[get_graph] = lambda: graph
    yield graph
    app.dependency_overrides.clear()
