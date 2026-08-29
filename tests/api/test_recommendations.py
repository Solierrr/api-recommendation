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


def test_get_recommendations_returns_empty_when_no_candidates(client, override_session, auth_headers):
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


def test_get_recommendations_rejects_both_rating_fields(client, override_session, auth_headers):
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
