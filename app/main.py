import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import health
from app.config import settings
from app.database import graph_service, postgres_service
from app.feeds.offers import router as offers
from app.feeds.professionals import router as professionals
from app.feeds.suppliers import router as suppliers
from app.observability.errors import register_error_handlers
from app.observability.observability import setup_observability

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

# ordem fixa: a observabilidade cria o span que os handlers de erro marcam
setup_observability(app, "api-recommendation")
register_error_handlers(app)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["Content-Type"],
)


app.include_router(health.router)
for feed in (professionals, offers, suppliers):
    app.include_router(feed.router)
    app.include_router(feed.public_router)
