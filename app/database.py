from typing import AsyncGenerator
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from app.config import settings

class Neo4jService:
    def __init__(self):
        self._driver: AsyncDriver | None = None

    async def connect(self):
        """Inicializa o driver Singleton usando as credenciais da nuvem."""
        self._driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
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