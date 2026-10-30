import logging
from collections.abc import Mapping
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry import trace
from starlette.exceptions import HTTPException

from app.observability.observability import TRACE_ID_HEADER, mark_error

logger = logging.getLogger(__name__)

GENERIC_BY_STATUS = {
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    406: "NOT_ACCEPTABLE",
    409: "CONFLICT",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_FAILED",
    429: "RATE_LIMITED",
    502: "DEPENDENCY_UNAVAILABLE",
    503: "DEPENDENCY_UNAVAILABLE",
}


class ApiError(Exception):
    def __init__(self, status: int, error_code: str, detail: str, **extra):
        super().__init__(detail)
        self.status = status
        self.error_code = error_code
        self.detail = detail
        self.extra = extra


class FeedError(ApiError):
    status_code = 500

    def __init__(self, code: str, message: str):
        super().__init__(self.status_code, code, message)
        self.code = code
        self.message = message


class ContextNotFoundError(FeedError):
    status_code = 404


class FeedDataUnavailableError(FeedError):
    status_code = 422


class FeedUnavailableError(FeedError):
    status_code = 503


class GraphUnavailableError(Exception):
    pass


class SnapshotUnavailableError(GraphUnavailableError):
    pass


def problem(
    request: Request,
    status: int,
    error_code: str,
    detail: str,
    headers: Mapping[str, str] | None = None,
    **extra,
) -> JSONResponse:
    span = trace.get_current_span().get_span_context()
    trace_id = {"traceId": format(span.trace_id, "032x")} if span.is_valid else {}
    body = {
        "type": "about:blank",
        "title": error_code,
        "status": status,
        "errorCode": error_code,
        "detail": detail,
        "instance": request.url.path,
        "timestamp": datetime.now(UTC).isoformat(),
        **trace_id,
        **extra,
    }
    response = JSONResponse(body, status_code=status, media_type="application/problem+json", headers=headers)
    # o 500 sai pelo ServerErrorMiddleware, fora do middleware de X-Trace-Id -> header posto aqui também
    if trace_id:
        response.headers[TRACE_ID_HEADER] = trace_id["traceId"]
    return response


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        mark_error(exc)
        return problem(request, exc.status, exc.error_code, exc.detail, **exc.extra)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        mark_error(exc)
        code = GENERIC_BY_STATUS.get(exc.status_code, "INTERNAL_ERROR")
        return problem(request, exc.status_code, code, str(exc.detail), headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        mark_error(exc)
        errors = [
            {
                "field": ".".join(str(part) for part in error["loc"][1:]),
                "errorCode": "VALIDATION_FAILED",
                "detail": error["msg"],
            }
            for error in exc.errors()
        ]
        return problem(
            request, 422, "VALIDATION_FAILED", "Erro de validação nos campos da requisição.", errors=errors
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        mark_error(exc)
        logger.exception("Falha inesperada ao atender %s", request.url.path)
        return problem(request, 500, "INTERNAL_ERROR", "Ocorreu um erro interno inesperado.")
