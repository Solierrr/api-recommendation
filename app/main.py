from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import neo4j_service
from app.api import health, recommentation



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ligar a API: Conecta ao Neo4j
    await neo4j_service.connect()
    print("Conexão com Neo4j estabelecida!")
    yield
    # Desligar a API: Fecha as conexões
    await neo4j_service.close()
    print("Conexão com Neo4j encerrada.")

app = FastAPI(title="Motor de Recomendação B2B", lifespan=lifespan)

# Registrando a rota de healthcheck
for routes in (health.router, recommentation.router):
    app.include_router(health.router)
