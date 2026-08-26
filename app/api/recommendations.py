from typing import Annotated

from fastapi import APIRouter, Depends
from neo4j import AsyncSession
from app.database import neo4j_service
from app.core.candidate_service import CandidateService

router = APIRouter()

@router.get("/candidates/{service_name}")
async def get_candidates(
    service_name: str,
    session: Annotated[AsyncSession, Depends(neo4j_service.get_session)],
    min_level: int = 2,
):
    service = CandidateService(session)
    return await service.fetch_candidate_pool(service_name, min_level)