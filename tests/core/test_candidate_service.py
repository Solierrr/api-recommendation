from unittest.mock import AsyncMock, patch

import pytest

from app.core.candidate_service import CandidateService


@pytest.mark.asyncio
async def test_fetch_candidate_pool_returns_first_result_without_fallback():
    session = object()
    service = CandidateService(session)
    expected = [{"candidate_id": "prof_1"}]

    with patch(
        "app.core.candidate_service.CandidateRepository.find_candidates_by_service",
        new=AsyncMock(return_value=expected),
    ) as mocked:
        result = await service.fetch_candidate_pool("Desenvolvimento Python", min_level=3)

    assert result == expected
    mocked.assert_awaited_once_with(
        session=session, service_name="Desenvolvimento Python", min_qualification_level=3
    )


@pytest.mark.asyncio
async def test_fetch_candidate_pool_falls_back_to_level_one_when_empty():
    session = object()
    service = CandidateService(session)
    fallback_result = [{"candidate_id": "prof_2"}]

    mocked = AsyncMock(side_effect=[[], fallback_result])
    with patch(
        "app.core.candidate_service.CandidateRepository.find_candidates_by_service",
        new=mocked,
    ):
        result = await service.fetch_candidate_pool("Serviço Raro", min_level=4)

    assert result == fallback_result
    assert mocked.await_count == 2
    first_call_kwargs = mocked.await_args_list[0].kwargs
    second_call_kwargs = mocked.await_args_list[1].kwargs
    assert first_call_kwargs["min_qualification_level"] == 4
    assert second_call_kwargs["min_qualification_level"] == 1


@pytest.mark.asyncio
async def test_fetch_candidate_pool_does_not_fallback_when_min_level_is_one():
    session = object()
    service = CandidateService(session)

    mocked = AsyncMock(return_value=[])
    with patch(
        "app.core.candidate_service.CandidateRepository.find_candidates_by_service",
        new=mocked,
    ):
        result = await service.fetch_candidate_pool("Serviço Inexistente", min_level=1)

    assert result == []
    mocked.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_candidate_pool_no_fallback_when_results_found():
    session = object()
    service = CandidateService(session)
    expected = [{"candidate_id": "prof_3"}]

    mocked = AsyncMock(return_value=expected)
    with patch(
        "app.core.candidate_service.CandidateRepository.find_candidates_by_service",
        new=mocked,
    ):
        result = await service.fetch_candidate_pool("Arquitetura Cloud", min_level=5)

    assert result == expected
    mocked.assert_awaited_once()
