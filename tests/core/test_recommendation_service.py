from unittest.mock import AsyncMock, patch

import pytest

from app.core.recommendation_service import RecommendationService


@pytest.mark.asyncio
async def test_get_recommendations_orders_by_score_descending():
    session = object()
    service = RecommendationService(session)

    candidates = [
        {"candidate_id": "prof_low", "avg_qualification_score": 2.0},
        {"candidate_id": "prof_high", "avg_qualification_score": 5.0},
        {"candidate_id": "prof_mid", "avg_qualification_score": 3.5},
    ]

    with patch.object(
        service.candidate_service,
        "fetch_candidate_pool",
        new=AsyncMock(return_value=candidates),
    ):
        result = await service.get_recommendations("Desenvolvimento Python")

    ids_in_order = [c["candidate_id"] for c in result]
    assert ids_in_order == ["prof_high", "prof_mid", "prof_low"]


@pytest.mark.asyncio
async def test_get_recommendations_respects_limit():
    session = object()
    service = RecommendationService(session)

    candidates = [{"avg_qualification_score": float(i)} for i in range(1, 6)]

    with patch.object(
        service.candidate_service,
        "fetch_candidate_pool",
        new=AsyncMock(return_value=candidates),
    ):
        result = await service.get_recommendations("Serviço X", limit=2)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_recommendations_propagates_min_level_to_candidate_service():
    session = object()
    service = RecommendationService(session)

    mocked = AsyncMock(return_value=[])
    with patch.object(service.candidate_service, "fetch_candidate_pool", new=mocked):
        await service.get_recommendations("Serviço X", min_level=4, limit=10)

    mocked.assert_awaited_once_with("Serviço X", 4)


@pytest.mark.asyncio
async def test_get_recommendations_returns_empty_list_when_no_candidates():
    session = object()
    service = RecommendationService(session)

    with patch.object(
        service.candidate_service, "fetch_candidate_pool", new=AsyncMock(return_value=[])
    ):
        result = await service.get_recommendations("Serviço Inexistente")

    assert result == []
