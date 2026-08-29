import pytest

from app.config import settings
from app.core.errors import RecommendationDataUnavailableError
from app.core.recommendation_service import RecommendationService


def test_candidate_pool_overflow_fails_instead_of_returning_wrong_top_n(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "RECOMMENDATION_POOL_LIMIT", 10)

    with pytest.raises(RecommendationDataUnavailableError) as error:
        RecommendationService._bounded_candidates([{} for _ in range(11)])

    assert error.value.code == "CANDIDATE_POOL_TOO_LARGE"
