from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.recommendations import require_recommendation_key
from app.config import settings
from app.core.errors import ContextNotFoundError, SnapshotUnavailableError
from app.core.recommendation_service import RecommendationService
from app.database import neo4j_service
from app.main import app


async def fake_read_session():
    yield object()


app.dependency_overrides[neo4j_service.get_read_session] = fake_read_session
client = TestClient(app)


def panel_response(context_id: UUID, strategy: str) -> dict:
    return {
        "context": {
            "type": "local_unit",
            "id": context_id,
            "strategy": strategy,
            "generated_at": "2026-04-10T12:00:00Z",
            "sync_version": uuid4(),
        },
        "items": [],
        "warnings": [],
    }


def test_panel_endpoint_validates_strategy_before_service(monkeypatch) -> None:
    context_id = uuid4()

    response = client.get(
        f"/recommendations/solar-panels/units/{context_id}",
        params={"strategy": "not-a-strategy"},
    )

    assert response.status_code == 422


def test_panel_endpoint_returns_typed_envelope(monkeypatch) -> None:
    context_id = uuid4()

    async def recommend_panels(_self, local_unit_id, strategy):
        return panel_response(local_unit_id, strategy.value)

    monkeypatch.setattr(RecommendationService, "recommend_panels", recommend_panels)

    response = client.get(
        f"/recommendations/solar-panels/units/{context_id}",
        params={"strategy": "best_value"},
    )

    assert response.status_code == 200
    assert response.json()["context"]["strategy"] == "best_value"
    assert response.json()["items"] == []


def test_profession_context_not_found_is_sanitized(monkeypatch) -> None:
    async def recommend_professionals(_self, _profession_id, _strategy):
        raise ContextNotFoundError("PROFESSION_NOT_FOUND", "Não encontrada")

    monkeypatch.setattr(
        RecommendationService,
        "recommend_professionals",
        recommend_professionals,
    )

    response = client.get(
        f"/recommendations/professionals/professions/{uuid4()}",
        params={"strategy": "top_rated"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PROFESSION_NOT_FOUND"


def test_snapshot_unavailable_returns_503(monkeypatch) -> None:
    async def recommend_technicians(_self, _service_id, _strategy):
        raise SnapshotUnavailableError("SNAPSHOT_UNAVAILABLE", "Snapshot indisponível")

    monkeypatch.setattr(
        RecommendationService,
        "recommend_technicians",
        recommend_technicians,
    )

    response = client.get(
        f"/recommendations/technicians/services/{uuid4()}",
        params={"strategy": "least_loaded"},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "SNAPSHOT_UNAVAILABLE"


def test_invalid_uuid_is_rejected() -> None:
    response = client.get(
        "/recommendations/technicians/services/not-a-uuid",
        params={"strategy": "least_loaded"},
    )

    assert response.status_code == 422


def test_recommendation_key_is_enforced_when_configured(monkeypatch) -> None:
    key = "recommendation-key-with-at-least-32-characters"
    monkeypatch.setattr(settings, "RECOMMENDATION_API_KEY", SecretStr(key))

    with pytest.raises(HTTPException) as error:
        require_recommendation_key(None)

    assert error.value.status_code == 401
    assert require_recommendation_key(key) is None


def test_recommendation_auth_runs_before_neo4j_dependency(monkeypatch) -> None:
    opened_sessions = []

    async def tracked_read_session():
        opened_sessions.append(True)
        yield object()

    monkeypatch.setattr(
        settings,
        "RECOMMENDATION_API_KEY",
        SecretStr("recommendation-key-with-at-least-32-characters"),
    )
    app.dependency_overrides[neo4j_service.get_read_session] = tracked_read_session
    try:
        response = client.get(
            f"/recommendations/professionals/professions/{uuid4()}",
            params={"strategy": "top_rated"},
        )
    finally:
        app.dependency_overrides[neo4j_service.get_read_session] = fake_read_session

    assert response.status_code == 401
    assert opened_sessions == []
