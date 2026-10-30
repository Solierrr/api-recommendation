import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import health
from app.config import settings
from app.database import graph_service, postgres_service
from app.errors import register_error_handlers
from app.feeds.offers import router as offers
from app.feeds.professionals import router as professionals
from app.feeds.suppliers import router as suppliers
from app.openapi import install_openapi
from app.version import VERSION

logger = logging.getLogger(__name__)
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)

DESCRIPTION = (
    "Motor de feeds da plataforma: recomenda profissionais, ofertas de placas solares e fornecedores "
    "para as telas de feed do marketplace. O ranking vem de um grafo no Neo4j, projeção somente leitura "
    "do PostgreSQL do api-core; sem o grafo, os feeds respondem com uma amostra dos itens elegíveis lida "
    "do PostgreSQL. Os feeds em /feeds/* são chamados por serviço e exigem a chave de serviço do chamador "
    "no cabeçalho X-Service-Key; os feeds em /public/feeds/* são abertos e cacheáveis."
)

TAGS = [
    {"name": "Feeds", "description": "Feeds ranqueados para serviços, protegidos pela chave de serviço."},
    {"name": "Feeds públicos", "description": "Amostras abertas dos feeds, sem chave e com cache público."},
    {
        "name": "Saúde",
        "description": "Vivo e pronto do serviço, usados pelo Render, pelo GKE e pelo keepalive.",
    },
]


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
    title="Solaria — api-recommendation",
    description=DESCRIPTION,
    version=VERSION,
    contact={"name": "Solaria", "url": "https://github.com/Solierrr"},
    license_info={"name": "CC0-1.0", "url": "https://creativecommons.org/publicdomain/zero/1.0/"},
    servers=[
        {"url": "https://api-recommendation-qlml.onrender.com", "description": "QA"},
        {"url": "http://localhost:8000", "description": "Local"},
    ],
    openapi_tags=TAGS,
    lifespan=lifespan,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
    redoc_url=None,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
        "tagsSorter": "alpha",
        "operationsSorter": "alpha",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["Content-Type"],
)
register_error_handlers(app)
install_openapi(app)

app.include_router(health.router)
for feed in (professionals, offers, suppliers):
    app.include_router(feed.router)
    app.include_router(feed.public_router)
