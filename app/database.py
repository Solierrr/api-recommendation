import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from neo4j import READ_ACCESS, AsyncDriver, AsyncGraphDatabase, AsyncSession
from neo4j.exceptions import AuthError, ServiceUnavailable, SessionExpired

from app.config import settings
from app.errors import GraphUnavailableError

logger = logging.getLogger(__name__)

_GRAPH_FAILURES = (ServiceUnavailable, SessionExpired, AuthError, TimeoutError, OSError)


class GraphService:
    def __init__(self) -> None:
        self._driver: AsyncDriver | None = None
        self._retry_at = 0.0

    @property
    def configured(self) -> bool:
        return settings.graph_configured

    @property
    def available(self) -> bool:
        return self._driver is not None and time.monotonic() >= self._retry_at

    async def connect(self) -> None:
        uri = settings.DB_NEO4J_URI
        password = settings.DB_NEO4J_PASSWORD
        if not uri or password is None:
            logger.info("Neo4j não configurado; os feeds responderão 503 até que ele seja configurado")
            return
        self._driver = AsyncGraphDatabase.driver(
            uri,
            auth=(settings.DB_NEO4J_USER, password.get_secret_value()),
            connection_timeout=settings.GRAPH_TIMEOUT_SECONDS,
            connection_acquisition_timeout=settings.GRAPH_TIMEOUT_SECONDS,
            max_connection_pool_size=20,
        )
        try:
            await self._driver.verify_connectivity()
            logger.info("Conexão com Neo4j estabelecida")
        except _GRAPH_FAILURES as error:
            self._mark_unavailable(error)

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None

    def _mark_unavailable(self, error: Exception) -> None:
        self._retry_at = time.monotonic() + settings.GRAPH_RETRY_AFTER_SECONDS
        logger.warning(
            "Neo4j indisponível (%s); novas consultas aguardam %ss",
            error,
            settings.GRAPH_RETRY_AFTER_SECONDS,
        )

    @asynccontextmanager
    async def read_session(self) -> AsyncIterator[AsyncSession]:
        if self._driver is None:
            raise GraphUnavailableError("Neo4j não configurado")
        if time.monotonic() < self._retry_at:
            raise GraphUnavailableError("Neo4j em período de espera após falha")
        try:
            async with self._driver.session(
                database=settings.DB_NEO4J_FEED,
                default_access_mode=READ_ACCESS,
            ) as session:
                yield session
        except _GRAPH_FAILURES as error:
            self._mark_unavailable(error)
            raise GraphUnavailableError(str(error)) from error


graph_service = GraphService()
