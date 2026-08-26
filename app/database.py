import os
from collections.abc import AsyncGenerator

import certifi
from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession

from app.config import settings

# Em alguns ambientes (ex: Windows sem a CA raiz atualizada no repositório do
# sistema), a verificação TLS do driver do Neo4j pode falhar mesmo com um
# certificado de servidor válido. Apontamos explicitamente para o bundle de
# CAs confiáveis do certifi, sem desabilitar a verificação do certificado.
os.environ.setdefault("SSL_CERT_FILE", certifi.where())


class Neo4jService:
    def __init__(self):
        self._driver: AsyncDriver | None = None

    async def connect(self):
        """Inicializa o driver Singleton usando as credenciais da nuvem."""
        self._driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        await self._driver.verify_connectivity()

    async def close(self):
        """Encerra o pool de conexões."""
        if self._driver:
            await self._driver.close()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Gera uma sessão efêmera para cada requisição HTTP."""
        if not self._driver:
            raise RuntimeError("Driver Neo4j não foi inicializado.")
        async with self._driver.session() as session:
            yield session


neo4j_service = Neo4jService()
