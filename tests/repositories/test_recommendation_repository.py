import pytest

from app.repositories.recommendation_repository import RecommendationRepository


class FakeResult:
    async def data(self):
        return []


class FakeSession:
    def __init__(self):
        self.parameters = None

    async def run(self, _query, **parameters):
        self.parameters = parameters
        return FakeResult()


def test_candidate_queries_fetch_one_extra_row_instead_of_silent_truncation() -> None:
    for query in (
        RecommendationRepository.PANEL_CANDIDATES,
        RecommendationRepository.PROFESSIONAL_CANDIDATES,
        RecommendationRepository.TECHNICIAN_CANDIDATES,
    ):
        assert "LIMIT $fetch_limit" in query
        assert "$pool_limit" not in query


@pytest.mark.asyncio
async def test_repository_requests_one_row_beyond_pool_limit() -> None:
    session = FakeSession()

    await RecommendationRepository.get_panel_candidates(
        session,
        "version",
        pool_limit=500,
    )

    assert session.parameters["fetch_limit"] == 501


def test_assigned_technician_is_excluded_across_all_affiliations() -> None:
    query = RecommendationRepository.TECHNICIAN_CANDIDATES

    assert "(technician)<-[:OF_TECHNICIAN]-(assigned_affiliation" in query
    assert "(affiliation)-[:ASSIGNED_TO]" not in query


def test_panel_query_filters_invalid_numeric_models() -> None:
    query = RecommendationRepository.PANEL_CANDIDATES

    assert "model.power_wp > 0" in query
    assert "model.dimension > 0" in query
    assert "model.weight > 0" in query
    assert "model.efficiency <= 100" in query
