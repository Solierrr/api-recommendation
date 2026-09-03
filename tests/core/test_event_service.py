from unittest.mock import AsyncMock, patch

import pytest

from app.core.event_service import EventService
from app.repositories.event_repository import EventLogResult
from app.schemas.event import EventCreate, EventType


@pytest.mark.asyncio
async def test_register_event_delegates_to_repository_with_unwrapped_enum():
    session = object()
    service = EventService(session)
    event = EventCreate(user_id="empresa_1", candidate_id="prof_1", event_type=EventType.HIRE)

    with patch(
        "app.core.event_service.EventRepository.log_event",
        new=AsyncMock(return_value=EventLogResult.CREATED),
    ) as mocked:
        result = await service.register_event(event)

    assert result is EventLogResult.CREATED
    mocked.assert_awaited_once_with(
        session=session, user_id="empresa_1", candidate_id="prof_1", event_type="HIRE"
    )


@pytest.mark.asyncio
async def test_register_event_propagates_repository_validation_result():
    session = object()
    service = EventService(session)
    event = EventCreate(user_id="empresa_1", candidate_id="prof_inexistente", event_type=EventType.CLICK)

    with patch(
        "app.core.event_service.EventRepository.log_event",
        new=AsyncMock(return_value=EventLogResult.CANDIDATE_NOT_FOUND),
    ):
        result = await service.register_event(event)

    assert result is EventLogResult.CANDIDATE_NOT_FOUND
