import pytest

from app.repositories.candidate_repository import CandidateRepository
from tests.fakes import FakeResult, FakeSession


@pytest.mark.asyncio
async def test_find_candidates_by_service_returns_repository_data():
    expected = [
        {
            "candidate_id": "prof_1",
            "name": "Ana Silva",
            "service": "Desenvolvimento Python",
            "qualifications": ["FastAPI", "Neo4j"],
            "average_rating": 4.5,
            "review_count": 8,
        }
    ]
    session = FakeSession(result=FakeResult(data_return=expected))

    result = await CandidateRepository.find_candidates_by_service(
        session=session,
        service_name="Desenvolvimento Python",
        min_rating=4.0,
        limit=20,
    )

    assert result == expected


@pytest.mark.asyncio
async def test_find_candidates_by_service_passes_snapshot_query_parameters():
    session = FakeSession(result=FakeResult(data_return=[]))

    await CandidateRepository.find_candidates_by_service(
        session=session,
        service_name="Arquitetura Cloud",
        min_rating=3.5,
        limit=25,
    )

    query, params = session.calls[0]
    assert "state.active_version" in query
    assert "Technician" in query
    assert params == {
        "source": "api-core",
        "service_name": "Arquitetura Cloud",
        "min_rating": 3.5,
        "limit": 25,
    }


@pytest.mark.asyncio
async def test_find_candidates_by_service_uses_safe_defaults():
    session = FakeSession(result=FakeResult(data_return=[]))

    await CandidateRepository.find_candidates_by_service(
        session=session,
        service_name="Serviço X",
    )

    _, params = session.calls[0]
    assert params["min_rating"] == 0
    assert params["limit"] == 50


@pytest.mark.asyncio
async def test_find_candidates_by_service_returns_empty_list_when_no_matches():
    session = FakeSession(result=FakeResult(data_return=[]))

    result = await CandidateRepository.find_candidates_by_service(
        session=session,
        service_name="Serviço Inexistente",
    )

    assert result == []
