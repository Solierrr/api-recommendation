from hmac import compare_digest
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

_recommendation_key_header = APIKeyHeader(
    name="X-Recommendation-Key",
    scheme_name="RecommendationApiKey",
    auto_error=False,
)


def require_recommendation_key(
    provided_key: Annotated[str | None, Security(_recommendation_key_header)],
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
