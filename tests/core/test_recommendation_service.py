from unittest.mock import AsyncMock, patch

import pytest

from app.config import settings
from app.core.errors import RecommendationDataUnavailableError
from app.core.recommendation_service import RecommendationService


def candidate(candidate_id: str, rating: float, reviews: int) -> dict:
    return {
        "candidate_id": candidate_id,
        "average_rating": rating,
        "review_count": reviews,
    }


@pytest.mark.asyncio
async def test_get_recommendations_orders_by_score_descending():
    service = RecommendationService(object())
    candidates = [
        candidate("prof_low", 2.0, 5),
        candidate("prof_high", 5.0, 2),
        candidate("prof_mid", 3.5, 9),
    ]
    with patch.object(
        service.candidate_service,
        "fetch_candidate_pool",
        new=AsyncMock(return_value=candidates),
    ):
        result = await service.get_recommendations("Desenvolvimento Python")

    assert [item["candidate_id"] for item in result] == [
        "prof_high",
        "prof_mid",
        "prof_low",
    ]


@pytest.mark.asyncio
async def test_get_recommendations_uses_review_count_as_tiebreaker():
    service = RecommendationService(object())
    candidates = [candidate("few", 4.0, 2), candidate("many", 4.0, 20)]
    with patch.object(
        service.candidate_service,
        "fetch_candidate_pool",
        new=AsyncMock(return_value=candidates),
    ):
        result = await service.get_recommendations("Serviço X")

    assert [item["candidate_id"] for item in result] == ["many", "few"]


@pytest.mark.asyncio
async def test_get_recommendations_respects_limit():
    service = RecommendationService(object())
    candidates = [candidate(str(index), float(index), index) for index in range(1, 6)]
    with patch.object(
        service.candidate_service,
        "fetch_candidate_pool",
        new=AsyncMock(return_value=candidates),
    ):
        result = await service.get_recommendations("Serviço X", limit=2)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_recommendations_propagates_min_rating_to_candidate_service():
    service = RecommendationService(object())
    mocked = AsyncMock(return_value=[])
    with patch.object(service.candidate_service, "fetch_candidate_pool", new=mocked):
        await service.get_recommendations("Serviço X", min_rating=4.0, limit=10)

    mocked.assert_awaited_once_with("Serviço X", 4.0)


@pytest.mark.asyncio
async def test_get_recommendations_returns_empty_list_when_no_candidates():
    service = RecommendationService(object())
    with patch.object(
        service.candidate_service,
        "fetch_candidate_pool",
        new=AsyncMock(return_value=[]),
    ):
        result = await service.get_recommendations("Serviço Inexistente")

    assert result == []


def test_candidate_pool_overflow_fails_instead_of_returning_wrong_top_n(monkeypatch) -> None:
    monkeypatch.setattr(settings, "RECOMMENDATION_POOL_LIMIT", 10)
    oversized_pool = [{} for _ in range(11)]

    with pytest.raises(RecommendationDataUnavailableError) as error:
        RecommendationService._bounded_candidates(oversized_pool)

    assert error.value.code == "CANDIDATE_POOL_TOO_LARGE"
