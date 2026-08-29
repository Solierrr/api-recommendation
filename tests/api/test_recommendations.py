from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.api.recommendations import require_recommendation_key
from app.config import settings
from app.core.errors import ContextNotFoundError, SnapshotUnavailableError
from app.core.recommendation_service import RecommendationService
from app.database import neo4j_service
from app.main import app
from tests.fakes import FakeResult, FakeSession


def candidate(candidate_id: str, rating: float, reviews: int) -> dict:
    return {
        "candidate_id": candidate_id,
        "name": f"Profissional {candidate_id}",
        "service": "Desenvolvimento Python",
        "qualifications": ["FastAPI"],
        "average_rating": rating,
        "review_count": reviews,
    }


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


def test_get_recommendations_requires_api_key(client, override_session):
    override_session(FakeSession(result=FakeResult(data_return=[])))

    response = client.post(
        "/recommendations",
        json={"service_name": "Desenvolvimento Python"},
    )

    assert response.status_code == 401


def test_get_recommendations_rejects_wrong_api_key(client, override_session):
    override_session(FakeSession(result=FakeResult(data_return=[])))

    response = client.post(
        "/recommendations",
        json={"service_name": "Desenvolvimento Python"},
        headers={"X-API-Key": "chave-errada"},
    )

    assert response.status_code == 401


def test_get_recommendations_returns_ranked_results(client, override_session, auth_headers):
    override_session(
        FakeSession(
            result=FakeResult(data_return=[candidate("prof_1", 5.0, 12), candidate("prof_2", 3.0, 4)])
        )
    )

    response = client.post(
        "/recommendations",
        json={"service_name": "Desenvolvimento Python", "min_level": 2, "limit": 5},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["data"][0]["candidate_id"] == "prof_1"
    assert body["data"][0]["avg_qualification_score"] == 5.0
    assert body["data"][0]["score"] >= body["data"][1]["score"]


def test_get_recommendations_accepts_min_rating(client, override_session, auth_headers):
    session = FakeSession(result=FakeResult(data_return=[]))
    override_session(session)

    response = client.post(
        "/recommendations",
        json={"service_name": "Desenvolvimento Python", "min_rating": 4.5},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert session.calls[0][1]["min_rating"] == 4.5


def test_get_recommendations_returns_empty_when_no_candidates(
    client,
    override_session,
    auth_headers,
):
    override_session(FakeSession(result=FakeResult(data_return=[])))

    response = client.post(
        "/recommendations",
        json={"service_name": "Serviço Inexistente"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {"total": 0, "data": []}


def test_get_recommendations_validates_request_body(client, override_session, auth_headers):
    override_session(FakeSession(result=FakeResult(data_return=[])))

    response = client.post("/recommendations", json={}, headers=auth_headers)

    assert response.status_code == 422


def test_get_recommendations_validates_min_level_range(client, override_session, auth_headers):
    override_session(FakeSession(result=FakeResult(data_return=[])))

    response = client.post(
        "/recommendations",
        json={"service_name": "X", "min_level": 99},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_get_recommendations_rejects_both_rating_fields(
    client,
    override_session,
    auth_headers,
):
    override_session(FakeSession(result=FakeResult(data_return=[])))

    response = client.post(
        "/recommendations",
        json={"service_name": "X", "min_level": 3, "min_rating": 3},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_get_recommendations_preserves_legacy_min_level_default(
    client,
    override_session,
    auth_headers,
):
    session = FakeSession(result=FakeResult(data_return=[]))
    override_session(session)

    response = client.post(
        "/recommendations",
        json={"service_name": "Desenvolvimento Python"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert session.calls[0][1]["min_rating"] == 2.0


def test_legacy_recommendations_preserves_openapi_contract(client):
    openapi = client.get("/openapi.json").json()
    operation = openapi["paths"]["/recommendations"]["post"]
    request_schema = openapi["components"]["schemas"]["RecommendationRequest"]
    min_level_schema = request_schema["properties"]["min_level"]

    assert operation["operationId"] == "get_recommendations_recommendations_post"
    assert operation["deprecated"] is True
    assert min_level_schema["type"] == "integer"
    assert min_level_schema["default"] == 2
    assert min_level_schema["minimum"] == 1
    assert min_level_schema["maximum"] == 5
    assert min_level_schema["deprecated"] is True


def test_panel_endpoint_validates_strategy_before_service(client, override_session):
    override_session(FakeSession())
    context_id = uuid4()

    response = client.get(
        f"/recommendations/solar-panels/units/{context_id}",
        params={"strategy": "not-a-strategy"},
    )

    assert response.status_code == 422


def test_panel_endpoint_returns_typed_envelope(client, override_session, monkeypatch):
    override_session(FakeSession())
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


def test_profession_context_not_found_is_sanitized(client, override_session, monkeypatch):
    override_session(FakeSession())

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


def test_snapshot_unavailable_returns_503(client, override_session, monkeypatch):
    override_session(FakeSession())

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


def test_invalid_uuid_is_rejected(client, override_session):
    override_session(FakeSession())

    response = client.get(
        "/recommendations/technicians/services/not-a-uuid",
        params={"strategy": "least_loaded"},
    )

    assert response.status_code == 422


def test_recommendation_key_is_enforced_when_configured(monkeypatch):
    key = "recommendation-key-with-at-least-32-characters"
    monkeypatch.setattr(settings, "RECOMMENDATION_API_KEY", SecretStr(key))

    with pytest.raises(HTTPException) as error:
        require_recommendation_key(None)

    assert error.value.status_code == 401
    assert require_recommendation_key(key) is None


def test_recommendation_auth_runs_before_neo4j_dependency(client, monkeypatch):
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
        app.dependency_overrides.pop(neo4j_service.get_read_session, None)

    assert response.status_code == 401
    assert opened_sessions == []
