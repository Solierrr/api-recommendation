from typing import Annotated

from fastapi import APIRouter, Depends, status
from neo4j import AsyncSession

from app.core.recommendation_service import RecommendationService
from app.database import neo4j_service
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.post("", response_model=RecommendationResponse, status_code=status.HTTP_200_OK)
async def get_recommendations(
    payload: RecommendationRequest,
    session: Annotated[AsyncSession, Depends(neo4j_service.get_session)],
):
    service = RecommendationService(session)
    results = await service.get_recommendations(
        service_name=payload.service_name,
        min_level=payload.min_level,
        limit=payload.limit,
    )
    return {"total": len(results), "data": results}
