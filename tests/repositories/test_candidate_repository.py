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
            "avg_qualification_score": 4.5,
        }
    ]
    session = FakeSession(result=FakeResult(data_return=expected))

    result = await CandidateRepository.find_candidates_by_service(
        session=session, service_name="Desenvolvimento Python", min_qualification_level=2
    )

    assert result == expected


@pytest.mark.asyncio
async def test_find_candidates_by_service_passes_correct_query_parameters():
    session = FakeSession(result=FakeResult(data_return=[]))

    await CandidateRepository.find_candidates_by_service(
        session=session, service_name="Arquitetura Cloud", min_qualification_level=3
    )

    assert len(session.calls) == 1
    _, params = session.calls[0]
    assert params["service_name"] == "Arquitetura Cloud"
    assert params["min_level"] == 3


@pytest.mark.asyncio
async def test_find_candidates_by_service_default_min_level_is_one():
    session = FakeSession(result=FakeResult(data_return=[]))

    await CandidateRepository.find_candidates_by_service(
        session=session, service_name="Serviço X"
    )

    _, params = session.calls[0]
    assert params["min_level"] == 1


@pytest.mark.asyncio
async def test_find_candidates_by_service_returns_empty_list_when_no_matches():
    session = FakeSession(result=FakeResult(data_return=[]))

    result = await CandidateRepository.find_candidates_by_service(
        session=session, service_name="Serviço Inexistente"
    )

    assert result == []
