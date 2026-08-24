from tests.fakes import FakeResult, FakeSession


def test_health_check_is_public_and_returns_200_when_db_ok(client, override_session):
    override_session(FakeSession(result=FakeResult(single_return={"status": 1})))

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "online"


def test_health_check_returns_503_when_db_query_fails(client, override_session):
    def _raise(query, params):
        raise RuntimeError("connection refused")

    override_session(FakeSession(result_factory=_raise))

    response = client.get("/health")

    assert response.status_code == 503
    # Nunca deve expor detalhes internos da exceção na resposta.
    assert "connection refused" not in response.text


def test_health_check_returns_503_when_db_returns_unexpected_value(client, override_session):
    override_session(FakeSession(result=FakeResult(single_return={"status": 0})))

    response = client.get("/health")

    assert response.status_code == 503
