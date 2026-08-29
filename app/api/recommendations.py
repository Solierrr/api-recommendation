import logging
from collections.abc import Awaitable
from hmac import compare_digest
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Security, status
from fastapi.security import APIKeyHeader
from neo4j import AsyncSession

from app.config import settings
from app.core.errors import (
    ContextNotFoundError,
    RecommendationDataUnavailableError,
    SnapshotUnavailableError,
)
from app.core.recommendation_service import RecommendationService
from app.database import neo4j_service
from app.schemas.recommendations import (
    PanelRecommendationResponse,
    PanelStrategy,
    ProfessionalRecommendationResponse,
    ProfessionalStrategy,
    TechnicianRecommendationResponse,
    TechnicianStrategy,
)
from app.schemas.responses import CandidateResponse

logger = logging.getLogger(__name__)

recommendation_key_header = APIKeyHeader(
    name="X-Recommendation-Key",
    scheme_name="RecommendationApiKey",
    auto_error=False,
)


def require_recommendation_key(
    provided_key: Annotated[str | None, Security(recommendation_key_header)],
) -> None:
    configured_key = settings.RECOMMENDATION_API_KEY
    if configured_key is None:
        if settings.APP_ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Autenticação das recomendações não configurada",
            )
        return

    if (
        provided_key is None
        or len(provided_key) > 512
        or not compare_digest(provided_key, configured_key.get_secret_value())
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de recomendação inválida",
            headers={"WWW-Authenticate": "ApiKey"},
        )


router = APIRouter(
    tags=["recommendations"],
    dependencies=[Depends(require_recommendation_key)],
)


async def _execute_recommendation(operation: Awaitable[Any]) -> Any:
    try:
        return await operation
    except SnapshotUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": error.code, "message": error.message},
        ) from None
    except ContextNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": error.code, "message": error.message},
        ) from None
    except RecommendationDataUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": error.code, "message": error.message},
        ) from None
    except Exception:
        logger.exception("Falha inesperada ao gerar recomendações")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "RECOMMENDATION_FAILED",
                "message": "Não foi possível gerar a recomendação.",
            },
        ) from None


@router.get(
    "/recommendations/solar-panels/units/{local_unit_id}",
    response_model=PanelRecommendationResponse,
)
async def recommend_solar_panels(
    local_unit_id: UUID,
    strategy: Annotated[PanelStrategy, Query()],
    session: Annotated[AsyncSession, Depends(neo4j_service.get_read_session)],
):
    return await _execute_recommendation(
        RecommendationService(session).recommend_panels(local_unit_id, strategy)
    )


@router.get(
    "/recommendations/professionals/professions/{profession_id}",
    response_model=ProfessionalRecommendationResponse,
)
async def recommend_professionals(
    profession_id: UUID,
    strategy: Annotated[ProfessionalStrategy, Query()],
    session: Annotated[AsyncSession, Depends(neo4j_service.get_read_session)],
):
    return await _execute_recommendation(
        RecommendationService(session).recommend_professionals(profession_id, strategy)
    )


@router.get(
    "/recommendations/technicians/services/{technical_service_id}",
    response_model=TechnicianRecommendationResponse,
)
async def recommend_technicians(
    technical_service_id: UUID,
    strategy: Annotated[TechnicianStrategy, Query()],
    session: Annotated[AsyncSession, Depends(neo4j_service.get_read_session)],
):
    return await _execute_recommendation(
        RecommendationService(session).recommend_technicians(
            technical_service_id, strategy
        )
    )


@router.get(
    "/candidates/{service_name}",
    response_model=list[CandidateResponse],
    deprecated=True,
)
async def get_candidates(
    service_name: Annotated[str, Path(min_length=1, max_length=100)],
    session: Annotated[AsyncSession, Depends(neo4j_service.get_read_session)],
    min_rating: Annotated[float, Query(ge=0, le=5)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 5,
):
    normalized_service_name = service_name.strip()
    if not normalized_service_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Nome do serviço não pode ser vazio",
        )

    return await _execute_recommendation(
        RecommendationService(session).get_recommendations(
            normalized_service_name,
            min_rating=min_rating,
            limit=limit,
        )
    )
