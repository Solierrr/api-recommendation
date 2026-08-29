import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import events, health, recommendations, sync
from app.config import settings
from app.core.sync_service import SyncService
from app.database import neo4j_service, postgres_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime_security()
    try:
        await postgres_service.connect()
        logger.info("Conexão somente leitura com PostgreSQL estabelecida")

        await neo4j_service.connect()
        logger.info("Conexão com Neo4j estabelecida")

        if settings.SYNC_ON_STARTUP:
            async with neo4j_service.write_session() as session:
                summary = await SyncService(postgres_service, session).synchronize()
            logger.info(
                "Sincronização inicial %s concluída: %s ofertas, %s profissionais, %s serviços técnicos",
                summary.sync_version,
                summary.panel_offers,
                summary.professionals,
                summary.technical_services,
            )

        yield
    finally:
        await neo4j_service.close()
        await postgres_service.close()
        logger.info("Conexões com Neo4j e PostgreSQL encerradas")


app = FastAPI(
    title="Motor de Recomendação B2B",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
)

app.include_router(health.router)
app.include_router(events.router)
app.include_router(recommendations.legacy_router)
app.include_router(recommendations.router)
app.include_router(sync.router)
