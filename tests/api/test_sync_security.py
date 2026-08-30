import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.sync import require_sync_key
from app.config import settings
from app.database import neo4j_service
from app.main import app

client = TestClient(app)


def test_sync_key_is_required(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SYNC_API_KEY", SecretStr("a" * 32))

    with pytest.raises(HTTPException) as error:
        require_sync_key(None)

    assert error.value.status_code == 401


def test_sync_key_uses_configured_secret(monkeypatch) -> None:
    key = "secure-test-key-with-more-than-32-characters"
    monkeypatch.setattr(settings, "SYNC_API_KEY", SecretStr(key))

    assert require_sync_key(key) is None


def test_sync_key_rejects_oversized_header(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SYNC_API_KEY", SecretStr("a" * 32))

    with pytest.raises(HTTPException) as error:
        require_sync_key("a" * 513)

    assert error.value.status_code == 401


def test_sync_auth_runs_before_neo4j_dependency(monkeypatch) -> None:
    opened_sessions = []

    async def tracked_write_session():
        opened_sessions.append(True)
        yield object()

    monkeypatch.setattr(settings, "SYNC_API_KEY", SecretStr("a" * 32))
    app.dependency_overrides[neo4j_service.get_write_session] = tracked_write_session
    try:
        response = client.post("/internal/sync/core")
    finally:
        app.dependency_overrides.pop(neo4j_service.get_write_session, None)

    assert response.status_code == 401
    assert opened_sessions == []
