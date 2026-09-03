import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.config import settings
from app.core.security import require_api_key
from tests.conftest import VALID_API_KEY


def test_require_api_key_accepts_valid_key():
    # Não deve lançar exceção.
    require_api_key(api_key=VALID_API_KEY)


def test_require_api_key_rejects_missing_key():
    with pytest.raises(HTTPException) as exc_info:
        require_api_key(api_key=None)

    assert exc_info.value.status_code == 401


def test_require_api_key_rejects_wrong_key():
    with pytest.raises(HTTPException) as exc_info:
        require_api_key(api_key="chave-errada")

    assert exc_info.value.status_code == 401


def test_require_api_key_rejects_empty_string():
    with pytest.raises(HTTPException) as exc_info:
        require_api_key(api_key="")

    assert exc_info.value.status_code == 401


def test_require_api_key_does_not_fallback_to_recommendation_key(monkeypatch):
    recommendation_key = "recommendation-key-with-at-least-32-characters"
    monkeypatch.setattr(settings, "API_KEY", None)
    monkeypatch.setattr(settings, "RECOMMENDATION_API_KEY", SecretStr(recommendation_key))

    with pytest.raises(HTTPException) as exc_info:
        require_api_key(api_key=recommendation_key)

    assert exc_info.value.status_code == 503
