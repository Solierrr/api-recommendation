import pytest
from pydantic import SecretStr

from app.config import Settings


def production_settings(**overrides) -> Settings:
    values = {
        "APP_ENVIRONMENT": "production",
        "APP_TIMEZONE": "UTC",
        "DOCS_ENABLED": False,
        "NEO4J_URI": "neo4j+s://neo4j.example.com",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": SecretStr("secret"),
        "DB_POSTGRES_HOST": "db.example.com",
        "DB_POSTGRES_PORT": 5432,
        "DB_POSTGRES_CORE": "recommendation",
        "DB_POSTGRES_USER": "reader",
        "DB_POSTGRES_PASSWORD": SecretStr("secret"),
        "DB_POSTGRES_SSLMODE": "require",
        "SYNC_API_KEY": SecretStr("a" * 32),
        "RECOMMENDATION_API_KEY": SecretStr("b" * 32),
        "API_KEY": SecretStr("c" * 32),
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_rejects_unencrypted_postgres() -> None:
    configured = production_settings(DB_POSTGRES_SSLMODE="disable")

    with pytest.raises(RuntimeError, match="DB_POSTGRES_SSLMODE"):
        configured.validate_runtime_security()


def test_production_rejects_public_documentation() -> None:
    configured = production_settings(DOCS_ENABLED=True)

    with pytest.raises(RuntimeError, match="DOCS_ENABLED"):
        configured.validate_runtime_security()


def test_production_requires_strong_sync_key() -> None:
    configured = production_settings(SYNC_API_KEY=SecretStr("short"))

    with pytest.raises(RuntimeError, match="SYNC_API_KEY"):
        configured.validate_runtime_security()


def test_secure_production_configuration_passes() -> None:
    production_settings().validate_runtime_security()


def test_production_rejects_unencrypted_neo4j() -> None:
    configured = production_settings(NEO4J_URI="bolt://neo4j.example.com")

    with pytest.raises(RuntimeError, match="NEO4J_URI"):
        configured.validate_runtime_security()


def test_production_requires_recommendation_key() -> None:
    configured = production_settings(RECOMMENDATION_API_KEY=SecretStr("short"))

    with pytest.raises(RuntimeError, match="RECOMMENDATION_API_KEY"):
        configured.validate_runtime_security()


def test_production_requires_distinct_api_keys() -> None:
    shared_key = SecretStr("same-secret-value-with-at-least-32-characters")
    configured = production_settings(
        SYNC_API_KEY=shared_key,
        RECOMMENDATION_API_KEY=shared_key,
    )

    with pytest.raises(RuntimeError, match="devem ser diferentes"):
        configured.validate_runtime_security()


def test_example_api_key_placeholders_are_invalid_in_production() -> None:
    configured = production_settings(
        SYNC_API_KEY=SecretStr("change-me-sync"),
        RECOMMENDATION_API_KEY=SecretStr("change-me-recommendation"),
    )

    with pytest.raises(RuntimeError, match="SYNC_API_KEY"):
        configured.validate_runtime_security()
