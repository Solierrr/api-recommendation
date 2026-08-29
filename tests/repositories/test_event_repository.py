import pytest

from app.repositories.event_repository import EventLogResult, EventRepository
from tests.fakes import FakeResult, FakeSession


@pytest.mark.asyncio
async def test_log_event_returns_created_when_event_is_persisted():
    session = FakeSession(result=FakeResult(single_return={"status": "CREATED"}))

    result = await EventRepository.log_event(
        session=session,
        user_id="empresa_1",
        candidate_id="prof_1",
        event_type="HIRE",
    )

    assert result is EventLogResult.CREATED


@pytest.mark.asyncio
async def test_log_event_distinguishes_candidate_not_found_or_ineligible():
    session = FakeSession(result=FakeResult(single_return={"status": "CANDIDATE_NOT_FOUND"}))

    result = await EventRepository.log_event(
        session=session,
        user_id="empresa_1",
        candidate_id="prof_inexistente",
        event_type="CLICK",
    )

    assert result is EventLogResult.CANDIDATE_NOT_FOUND


@pytest.mark.asyncio
async def test_log_event_distinguishes_unavailable_snapshot():
    session = FakeSession(result=FakeResult(single_return={"status": "SNAPSHOT_UNAVAILABLE"}))

    result = await EventRepository.log_event(
        session=session,
        user_id="empresa_1",
        candidate_id="prof_1",
        event_type="CLICK",
    )

    assert result is EventLogResult.SNAPSHOT_UNAVAILABLE


@pytest.mark.asyncio
async def test_log_event_validates_eligibility_and_keeps_telemetry_outside_snapshot():
    session = FakeSession(result=FakeResult(single_return={"status": "CREATED"}))

    await EventRepository.log_event(
        session=session,
        user_id="empresa_9",
        candidate_id="prof_9",
        event_type="VIEW",
    )

    query, params = session.calls[0]
    assert "OPTIONAL MATCH (state:SyncState" in query
    assert "state.active_version AS active_version" in query
    assert "candidate.user_active = true" in query
    assert ":REGISTERED_AS" in query
    assert "registration.source = $source" in query
    assert "registration.sync_version = active_version" in query
    assert "TelemetryEvent" in query
    assert "candidate_id: candidate.id" in query
    assert "validated_sync_version: active_version" in query
    assert params == {
        "source": "api-core",
        "candidate_id": "prof_9",
        "user_id": "empresa_9",
        "event_type": "VIEW",
    }
