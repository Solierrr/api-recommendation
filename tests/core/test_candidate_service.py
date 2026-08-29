from unittest.mock import AsyncMock, patch

import pytest

from app.core.candidate_service import CandidateService


@pytest.mark.asyncio
async def test_fetch_candidate_pool_applies_min_rating_strictly():
    session = object()
    service = CandidateService(session)
    expected = [{"candidate_id": "prof_1"}]

    with patch(
        "app.core.candidate_service.CandidateRepository.find_candidates_by_service",
        new=AsyncMock(return_value=expected),
    ) as mocked:
        result = await service.fetch_candidate_pool("Desenvolvimento Python", min_rating=3.5)

    assert result == expected
    mocked.assert_awaited_once_with(
        session=session,
        service_name="Desenvolvimento Python",
        min_rating=3.5,
    )


@pytest.mark.asyncio
async def test_fetch_candidate_pool_does_not_relax_rating_when_empty():
    service = CandidateService(object())
    mocked = AsyncMock(return_value=[])

    with patch(
        "app.core.candidate_service.CandidateRepository.find_candidates_by_service",
        new=mocked,
    ):
        result = await service.fetch_candidate_pool("Serviço Raro", min_rating=4.0)

    assert result == []
    mocked.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_candidate_pool_defaults_to_zero_rating():
    session = object()
    service = CandidateService(session)
    mocked = AsyncMock(return_value=[])

    with patch(
        "app.core.candidate_service.CandidateRepository.find_candidates_by_service",
        new=mocked,
    ):
        await service.fetch_candidate_pool("Serviço X")

    mocked.assert_awaited_once_with(
        session=session,
        service_name="Serviço X",
        min_rating=0,
    )
