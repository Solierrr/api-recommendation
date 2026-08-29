from hmac import compare_digest

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Valida a chave das rotas legadas sem enfraquecer as chaves novas."""
    configured_key = settings.API_KEY
    if configured_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Autenticação das rotas legadas não configurada",
        )

    if (
        api_key is None
        or len(api_key) > 512
        or not compare_digest(api_key, configured_key.get_secret_value())
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida ou ausente. Envie o header X-API-Key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
