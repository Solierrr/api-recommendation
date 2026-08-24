import hmac

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Dependência do FastAPI que exige um header X-API-Key válido.

    Usa comparação em tempo constante (hmac.compare_digest) para evitar
    vazamento de informação via timing attack.
    """
    if not api_key or not hmac.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida ou ausente. Envie o header X-API-Key.",
        )
