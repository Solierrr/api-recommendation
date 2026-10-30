from hmac import compare_digest
from typing import Annotated

from fastapi import Request, Security
from fastapi.security import APIKeyHeader

from app.config import settings
from app.errors import ApiError

MAX_KEY_LENGTH = 512

# Cabeçalho antigo do mcp-database. Fica fora do contrato e sai quando o chamador enviar X-Service-Key.
LEGACY_KEY_HEADER = "X-Recommendation-Key"
LEGACY_CALLER = "mcp-database"

service_key_header = APIKeyHeader(name="X-Service-Key", scheme_name="serviceKey", auto_error=False)


def _matches(provided: str, expected: str) -> bool:
    return len(provided) <= MAX_KEY_LENGTH and compare_digest(provided.encode(), expected.encode())


def _legacy_caller(request: Request) -> str | None:
    provided = request.headers.get(LEGACY_KEY_HEADER)
    configured = settings.RECOMMENDATION_API_KEY
    if provided and configured is not None and _matches(provided, configured.get_secret_value()):
        return LEGACY_CALLER
    return None


def require_caller(*callers: str):
    def dependency(
        request: Request,
        key: Annotated[str | None, Security(service_key_header)],
    ) -> str:
        caller = None
        if key:
            caller = next(
                (name for name, expected in settings.service_keys.items() if _matches(key, expected)), None
            )
        caller = caller or _legacy_caller(request)
        if caller is None:
            raise ApiError(401, "UNAUTHENTICATED", "Chave de serviço ausente ou inválida.")
        if caller not in callers:
            raise ApiError(403, "FORBIDDEN", "Serviço chamador não autorizado nesta rota.")
        return caller

    return dependency
