import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app import health
from app.config import settings
from app.database import graph_service, postgres_service
from app.errors import FeedError
from app.feeds.offers import router as offers
from app.feeds.professionals import router as professionals
from app.feeds.suppliers import router as suppliers

logger = logging.getLogger(__name__)
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime_security()
    try:
        await postgres_service.connect()
        logger.info("Conexão somente leitura com PostgreSQL estabelecida")
        await graph_service.connect()
        yield
    finally:
        await graph_service.close()
        await postgres_service.close()
        logger.info("Conexões com Neo4j e PostgreSQL encerradas")


app = FastAPI(
    title="Motor de Recomendação B2B",
    version="4.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
)


@app.exception_handler(FeedError)
async def feed_error_handler(request: Request, error: FeedError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"detail": {"code": error.code, "message": error.message}},
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, error: Exception) -> JSONResponse:
    logger.exception("Falha inesperada ao gerar recomendações")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": {
                "code": "RECOMMENDATION_FAILED",
                "message": "Não foi possível gerar a recomendação.",
            }
        },
    )


app.include_router(health.router)
for feed in (professionals, offers, suppliers):
    app.include_router(feed.router)
    app.include_router(feed.public_router)
