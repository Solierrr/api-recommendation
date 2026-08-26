import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health, recommendations
from app.database import neo4j_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ligar a API: Conecta ao Neo4j
    await neo4j_service.connect()
    logger.info("Conexão com Neo4j estabelecida!")
    yield
    # Desligar a API: Fecha as conexões
    await neo4j_service.close()
    logger.info("Conexão com Neo4j encerrada.")


app = FastAPI(title="Motor de Recomendação B2B", lifespan=lifespan)

# Registrando as rotas da aplicação
app.include_router(health.router)
app.include_router(recommendations.router)
