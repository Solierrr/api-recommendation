from tests.fakes import FakeResult, FakeSession


def test_get_recommendations_requires_api_key(client, override_session):
    override_session(FakeSession(result=FakeResult(data_return=[])))

    response = client.post("/recommendations", json={"service_name": "Desenvolvimento Python"})

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
    candidates = [
        {
            "candidate_id": "prof_1",
            "name": "Ana Silva",
            "service": "Desenvolvimento Python",
            "qualifications": ["FastAPI"],
            "avg_qualification_score": 5.0,
        },
        {
            "candidate_id": "prof_2",
            "name": "Carlos Souza",
            "service": "Desenvolvimento Python",
            "qualifications": ["FastAPI"],
            "avg_qualification_score": 3.0,
        },
    ]
    override_session(FakeSession(result=FakeResult(data_return=candidates)))

    response = client.post(
        "/recommendations",
        json={"service_name": "Desenvolvimento Python", "min_level": 2, "limit": 5},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["data"][0]["candidate_id"] == "prof_1"
    assert body["data"][0]["score"] >= body["data"][1]["score"]


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

    # service_name é obrigatório.
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
