from app.repositories.event_repository import EventLogResult
from tests.fakes import FakeResult, FakeSession


def event_result(status: EventLogResult) -> FakeResult:
    return FakeResult(single_return={"status": status.value})


def test_track_event_requires_api_key(client, override_session):
    override_session(FakeSession(result=event_result(EventLogResult.CREATED)))

    response = client.post(
        "/events",
        json={"user_id": "empresa_1", "candidate_id": "prof_1", "event_type": "CLICK"},
    )

    assert response.status_code == 401


def test_track_event_returns_201_when_created(client, override_session, auth_headers):
    override_session(FakeSession(result=event_result(EventLogResult.CREATED)))

    response = client.post(
        "/events",
        json={"user_id": "empresa_1", "candidate_id": "prof_1", "event_type": "HIRE"},
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["status"] == "success"


def test_track_event_returns_400_when_candidate_is_missing_or_ineligible(
    client,
    override_session,
    auth_headers,
):
    override_session(FakeSession(result=event_result(EventLogResult.CANDIDATE_NOT_FOUND)))

    response = client.post(
        "/events",
        json={"user_id": "empresa_1", "candidate_id": "prof_inexistente", "event_type": "VIEW"},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "inelegível" in response.json()["detail"]


def test_track_event_returns_503_when_snapshot_is_unavailable(
    client,
    override_session,
    auth_headers,
):
    override_session(FakeSession(result=event_result(EventLogResult.SNAPSHOT_UNAVAILABLE)))

    response = client.post(
        "/events",
        json={"user_id": "empresa_1", "candidate_id": "prof_1", "event_type": "VIEW"},
        headers=auth_headers,
    )

    assert response.status_code == 503
    assert "Snapshot ativo indisponível" in response.json()["detail"]


def test_track_event_validates_event_type(client, override_session, auth_headers):
    override_session(FakeSession(result=event_result(EventLogResult.CREATED)))

    response = client.post(
        "/events",
        json={"user_id": "empresa_1", "candidate_id": "prof_1", "event_type": "INVALIDO"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_track_event_validates_required_fields(client, override_session, auth_headers):
    override_session(FakeSession(result=event_result(EventLogResult.CREATED)))

    response = client.post("/events", json={}, headers=auth_headers)

    assert response.status_code == 422
