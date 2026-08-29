import pytest

from app.config import Settings

VALID_PRODUCTION_KEYS = {
    "SYNC_API_KEY": "s" * 32,
    "RECOMMENDATION_API_KEY": "r" * 32,
    "API_KEY": "a" * 32,
}


def production_settings(**overrides) -> Settings:
    values = {
        "APP_ENVIRONMENT": "production",
        "DOCS_ENABLED": False,
        "NEO4J_URI": "neo4j+s://neo4j.example.com",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "production-password",
        "DB_SSLMODE": "require",
        **VALID_PRODUCTION_KEYS,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_accepts_three_strong_distinct_api_keys():
    production_settings().validate_runtime_security()


@pytest.mark.parametrize("key_name", VALID_PRODUCTION_KEYS)
def test_production_requires_each_api_key(key_name):
    configured_settings = production_settings(**{key_name: None})

    with pytest.raises(RuntimeError, match=key_name):
        configured_settings.validate_runtime_security()


@pytest.mark.parametrize("key_name", VALID_PRODUCTION_KEYS)
@pytest.mark.parametrize("invalid_length", [31, 513])
def test_production_rejects_weak_or_oversized_api_keys(key_name, invalid_length):
    configured_settings = production_settings(**{key_name: "x" * invalid_length})

    with pytest.raises(RuntimeError, match=key_name):
        configured_settings.validate_runtime_security()


@pytest.mark.parametrize(
    ("first_key", "second_key"),
    [
        ("SYNC_API_KEY", "RECOMMENDATION_API_KEY"),
        ("SYNC_API_KEY", "API_KEY"),
        ("RECOMMENDATION_API_KEY", "API_KEY"),
    ],
)
def test_production_requires_api_keys_to_be_pairwise_distinct(first_key, second_key):
    configured_settings = production_settings(**{second_key: VALID_PRODUCTION_KEYS[first_key]})

    with pytest.raises(RuntimeError, match="devem ser diferentes entre si"):
        configured_settings.validate_runtime_security()


def test_non_production_does_not_require_api_keys():
    configured_settings = production_settings(
        APP_ENVIRONMENT="test",
        SYNC_API_KEY=None,
        RECOMMENDATION_API_KEY=None,
        API_KEY=None,
    )

    configured_settings.validate_runtime_security()
