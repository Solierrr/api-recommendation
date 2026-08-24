from unittest.mock import AsyncMock, patch

import pytest

from app.core.event_service import EventService
from app.schemas.event import EventCreate, EventType


@pytest.mark.asyncio
async def test_register_event_delegates_to_repository_with_unwrapped_enum():
    session = object()
    service = EventService(session)
    event = EventCreate(user_id="empresa_1", candidate_id="prof_1", event_type=EventType.HIRE)

    with patch(
        "app.core.event_service.EventRepository.log_event",
        new=AsyncMock(return_value=True),
    ) as mocked:
        result = await service.register_event(event)

    assert result is True
    mocked.assert_awaited_once_with(
        session=session, user_id="empresa_1", candidate_id="prof_1", event_type="HIRE"
    )


@pytest.mark.asyncio
async def test_register_event_returns_false_when_repository_fails():
    session = object()
    service = EventService(session)
    event = EventCreate(user_id="empresa_1", candidate_id="prof_inexistente", event_type=EventType.CLICK)

    with patch(
        "app.core.event_service.EventRepository.log_event",
        new=AsyncMock(return_value=False),
    ):
        result = await service.register_event(event)

    assert result is False
