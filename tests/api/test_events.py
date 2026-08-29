from tests.fakes import FakeResult, FakeSession


def test_track_event_requires_api_key(client, override_session):
    override_session(FakeSession(result=FakeResult(single_return={"r": "rel"})))

    response = client.post(
        "/events",
        json={"user_id": "empresa_1", "candidate_id": "prof_1", "event_type": "CLICK"},
    )

    assert response.status_code == 401


def test_track_event_returns_201_when_created(client, override_session, auth_headers):
    override_session(FakeSession(result=FakeResult(single_return={"r": "rel"})))

    response = client.post(
        "/events",
        json={"user_id": "empresa_1", "candidate_id": "prof_1", "event_type": "HIRE"},
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["status"] == "success"


def test_track_event_returns_400_when_candidate_not_found(client, override_session, auth_headers):
    override_session(FakeSession(result=FakeResult(single_return=None)))

    response = client.post(
        "/events",
        json={"user_id": "empresa_1", "candidate_id": "prof_inexistente", "event_type": "VIEW"},
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_track_event_validates_event_type(client, override_session, auth_headers):
    override_session(FakeSession(result=FakeResult(single_return={"r": "rel"})))

    response = client.post(
        "/events",
        json={"user_id": "empresa_1", "candidate_id": "prof_1", "event_type": "INVALIDO"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_track_event_validates_required_fields(client, override_session, auth_headers):
    override_session(FakeSession(result=FakeResult(single_return={"r": "rel"})))

    response = client.post("/events", json={}, headers=auth_headers)

    assert response.status_code == 422
