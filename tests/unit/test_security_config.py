import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings, settings
from app.security import require_recommendation_key

KEY = "k" * 40


@pytest.fixture
def secured_client():
    secured = FastAPI()

    @secured.get("/secret", dependencies=[Depends(require_recommendation_key)])
    def secret():
        return {"ok": True}

    return TestClient(secured)


def test_requests_are_open_when_no_key_is_configured_outside_production(secured_client):
    assert secured_client.get("/secret").status_code == 200


def test_requests_are_refused_when_no_key_is_configured_in_production(secured_client, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENVIRONMENT", "production")

    response = secured_client.get("/secret")

    assert response.status_code == 503


@pytest.mark.parametrize(
    "headers", [{}, {"X-Recommendation-Key": "errada"}, {"X-Recommendation-Key": "k" * 600}]
)
def test_requests_with_a_missing_or_wrong_key_are_unauthorized(secured_client, monkeypatch, headers):
    monkeypatch.setattr(settings, "RECOMMENDATION_API_KEY", SecretStr(KEY))

    response = secured_client.get("/secret", headers=headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "ApiKey"


def test_requests_with_the_right_key_are_accepted(secured_client, monkeypatch):
    monkeypatch.setattr(settings, "RECOMMENDATION_API_KEY", SecretStr(KEY))

    assert secured_client.get("/secret", headers={"X-Recommendation-Key": KEY}).status_code == 200


def production(**overrides) -> Settings:
    values = {
        "APP_ENVIRONMENT": "production",
        "DOCS_ENABLED": False,
        "RECOMMENDATION_API_KEY": SecretStr(KEY),
    }
    return Settings(_env_file=None, **{**values, **overrides})  # type: ignore[arg-type]


def test_production_settings_pass_when_everything_is_hardened():
    production().validate_runtime_security()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"DOCS_ENABLED": True}, "DOCS_ENABLED"),
        ({"RECOMMENDATION_API_KEY": None}, "RECOMMENDATION_API_KEY é obrigatória"),
        ({"RECOMMENDATION_API_KEY": SecretStr("curta")}, "entre 32 e 512"),
    ],
)
def test_production_settings_reject_weak_configuration(overrides, message):
    with pytest.raises(RuntimeError, match=message):
        production(**overrides).validate_runtime_security()


def test_non_production_skips_the_hardening_checks():
    Settings(_env_file=None, APP_ENVIRONMENT="development", DOCS_ENABLED=True).validate_runtime_security()


def test_in_cluster_bolt_uri_is_valid_in_production():
    production(
        DB_NEO4J_URI="bolt://feeddb:7687", DB_NEO4J_PASSWORD=SecretStr("senha"), DB_NEO4J_FEED="feeddb"
    ).validate_runtime_security()


def test_graph_is_configured_only_with_uri_and_password():
    assert not Settings(_env_file=None).graph_configured
    assert not Settings(_env_file=None, DB_NEO4J_URI="bolt://x:7687").graph_configured  # type: ignore[arg-type]
    configured = Settings(_env_file=None, DB_NEO4J_URI="bolt://x:7687", DB_NEO4J_PASSWORD=SecretStr("s"))  # type: ignore[arg-type]
    assert configured.graph_configured
