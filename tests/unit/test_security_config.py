import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from app.config import Settings, settings
from app.errors import register_error_handlers
from app.security import require_caller

KEY = "k" * 40
OTHER_KEY = "o" * 40


@pytest.fixture
def secured_client(monkeypatch):
    monkeypatch.setattr(settings, "SERVICE_KEY_MCP_DATABASE", SecretStr(KEY))
    monkeypatch.setattr(settings, "RECOMMENDATION_API_KEY", None)
    secured = FastAPI()
    register_error_handlers(secured)

    @secured.get("/secret", dependencies=[Depends(require_caller("mcp-database"))])
    def secret():
        return {"ok": True}

    @secured.get("/other", dependencies=[Depends(require_caller("api-core"))])
    def other():
        return {"ok": True}

    return TestClient(secured)


def test_the_caller_key_is_accepted(secured_client):
    assert secured_client.get("/secret", headers={"X-Service-Key": KEY}).status_code == 200


@pytest.mark.parametrize(
    "headers", [{}, {"X-Service-Key": "errada"}, {"X-Service-Key": "k" * 600}, {"X-Recommendation-Key": KEY}]
)
def test_a_missing_or_wrong_key_is_unauthenticated(secured_client, headers):
    response = secured_client.get("/secret", headers=headers)

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["errorCode"] == "UNAUTHENTICATED"
    assert KEY not in response.text


def test_a_valid_caller_that_the_route_does_not_accept_is_forbidden(secured_client):
    response = secured_client.get("/other", headers={"X-Service-Key": KEY})

    assert response.status_code == 403
    assert response.json()["errorCode"] == "FORBIDDEN"


def test_a_target_with_no_key_configured_refuses_everything(secured_client, monkeypatch):
    monkeypatch.setattr(settings, "SERVICE_KEY_MCP_DATABASE", None)

    assert secured_client.get("/secret", headers={"X-Service-Key": ""}).status_code == 401
    assert secured_client.get("/secret", headers={"X-Service-Key": KEY}).status_code == 401


def test_the_legacy_recommendation_key_still_identifies_the_mcp_database(secured_client, monkeypatch):
    monkeypatch.setattr(settings, "RECOMMENDATION_API_KEY", SecretStr(OTHER_KEY))

    assert secured_client.get("/secret", headers={"X-Recommendation-Key": OTHER_KEY}).status_code == 200
    assert secured_client.get("/secret", headers={"X-Recommendation-Key": KEY}).status_code == 401
    assert secured_client.get("/other", headers={"X-Recommendation-Key": OTHER_KEY}).status_code == 403


def production(**overrides) -> Settings:
    values = {
        "APP_ENVIRONMENT": "production",
        "DOCS_ENABLED": False,
        "DB_POSTGRES_SSLMODE": "require",
        "SERVICE_KEY_MCP_DATABASE": SecretStr(KEY),
    }
    return Settings(_env_file=None, **{**values, **overrides})  # type: ignore[arg-type]


def test_production_settings_pass_when_everything_is_hardened():
    production().validate_runtime_security()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"DB_POSTGRES_SSLMODE": "disable"}, "DB_POSTGRES_SSLMODE"),
        ({"DOCS_ENABLED": True}, "DOCS_ENABLED"),
        ({"SERVICE_KEY_MCP_DATABASE": None}, "SERVICE_KEY_MCP_DATABASE é obrigatória"),
        ({"SERVICE_KEY_MCP_DATABASE": SecretStr("curta")}, "entre 32 e 512"),
        ({"RECOMMENDATION_API_KEY": SecretStr("curta")}, "entre 32 e 512"),
    ],
)
def test_production_settings_reject_weak_configuration(overrides, message):
    with pytest.raises(RuntimeError, match=message):
        production(**overrides).validate_runtime_security()


def test_production_still_starts_with_only_the_legacy_key():
    production(
        SERVICE_KEY_MCP_DATABASE=None, RECOMMENDATION_API_KEY=SecretStr(KEY)
    ).validate_runtime_security()


def test_a_short_service_key_is_refused_in_every_environment():
    with pytest.raises(RuntimeError, match="entre 32 e 512"):
        Settings(_env_file=None, SERVICE_KEY_MCP_DATABASE=SecretStr("curta")).validate_runtime_security()  # type: ignore[arg-type]


def test_cors_origins_are_read_from_a_comma_separated_list():
    configured = Settings(_env_file=None, CORS_ALLOWED_ORIGINS=" https://a.example , ,http://b.example")  # type: ignore[arg-type]

    assert configured.cors_origins == ["https://a.example", "http://b.example"]


def test_non_production_skips_the_hardening_checks():
    Settings(
        _env_file=None, APP_ENVIRONMENT="development", DB_POSTGRES_SSLMODE="disable"
    ).validate_runtime_security()


def test_in_cluster_bolt_uri_is_valid_in_production():
    production(
        DB_NEO4J_URI="bolt://feeddb:7687", DB_NEO4J_PASSWORD=SecretStr("senha"), DB_NEO4J_FEED="feeddb"
    ).validate_runtime_security()


def test_invalid_sslmode_is_rejected_and_valid_one_is_normalized():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, DB_POSTGRES_SSLMODE="talvez")  # type: ignore[arg-type]
    assert Settings(_env_file=None, DB_POSTGRES_SSLMODE="REQUIRE").DB_POSTGRES_SSLMODE == "require"  # type: ignore[arg-type]


def test_graph_is_configured_only_with_uri_and_password():
    assert not Settings(_env_file=None).graph_configured
    assert not Settings(_env_file=None, DB_NEO4J_URI="bolt://x:7687").graph_configured  # type: ignore[arg-type]
    configured = Settings(_env_file=None, DB_NEO4J_URI="bolt://x:7687", DB_NEO4J_PASSWORD=SecretStr("s"))  # type: ignore[arg-type]
    assert configured.graph_configured


def test_postgres_dsn_is_built_from_the_shared_core_database():
    configured = Settings(
        _env_file=None,
        DB_POSTGRES_HOST="db.internal",
        DB_POSTGRES_PORT=6543,
        DB_POSTGRES_CORE="coredb",
    )  # type: ignore[arg-type]

    assert configured.postgres_dsn == "postgresql://db.internal:6543/coredb"
    assert Settings.model_fields["DB_POSTGRES_CORE"].default == "coredb"
