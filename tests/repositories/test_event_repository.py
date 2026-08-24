import pytest

from app.repositories.event_repository import EventRepository
from tests.fakes import FakeResult, FakeSession


@pytest.mark.asyncio
async def test_log_event_returns_true_when_relationship_created():
    session = FakeSession(result=FakeResult(single_return={"r": "some-relationship"}))

    result = await EventRepository.log_event(
        session=session, user_id="empresa_1", candidate_id="prof_1", event_type="HIRE"
    )

    assert result is True


@pytest.mark.asyncio
async def test_log_event_returns_false_when_candidate_does_not_exist():
    # MATCH não encontra o Profissional -> result.single() retorna None
    session = FakeSession(result=FakeResult(single_return=None))

    result = await EventRepository.log_event(
        session=session, user_id="empresa_1", candidate_id="prof_inexistente", event_type="CLICK"
    )

    assert result is False


@pytest.mark.asyncio
async def test_log_event_passes_correct_query_parameters():
    session = FakeSession(result=FakeResult(single_return={"r": "rel"}))

    await EventRepository.log_event(
        session=session, user_id="empresa_9", candidate_id="prof_9", event_type="VIEW"
    )

    assert len(session.calls) == 1
    _, params = session.calls[0]
    assert params == {
        "candidate_id": "prof_9",
        "user_id": "empresa_9",
        "event_type": "VIEW",
    }
