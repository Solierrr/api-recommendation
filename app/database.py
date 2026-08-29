from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from neo4j import (
    READ_ACCESS,
    WRITE_ACCESS,
    AsyncDriver,
    AsyncGraphDatabase,
    AsyncSession,
)

from app.config import settings


class PostgresService:
    def __init__(self):
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Cria um pool somente leitura para o PostgreSQL usado pelo api-core."""
        self._pool = await asyncpg.create_pool(
            dsn=settings.postgres_dsn,
            user=settings.DB_USERNAME,
            password=settings.DB_PASSWORD.get_secret_value(),
            ssl=settings.DB_SSLMODE,
            min_size=1,
            max_size=5,
            command_timeout=30,
            server_settings={
                "application_name": "api-recommendation",
                "statement_timeout": "30000",
                "idle_in_transaction_session_timeout": "30000",
            },
        )
        async with self._pool.acquire() as connection:
            await connection.execute("SET default_transaction_read_only = on")
            await connection.fetchval("SELECT 1")

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[asyncpg.Connection]:
        if not self._pool:
            raise RuntimeError("Pool PostgreSQL não foi inicializado.")
        async with (
            self._pool.acquire() as connection,
            connection.transaction(
                readonly=True,
                isolation="repeatable_read",
            ),
        ):
            yield connection

    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        async with self.connection() as connection:
            yield connection


class Neo4jService:
    def __init__(self):
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        self._driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD.get_secret_value()),
            connection_timeout=10,
            connection_acquisition_timeout=10,
            max_connection_pool_size=20,
        )
        await self._driver.verify_connectivity()

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None

    @asynccontextmanager
    async def read_session(self) -> AsyncIterator[AsyncSession]:
        if not self._driver:
            raise RuntimeError("Driver Neo4j não foi inicializado.")
        async with self._driver.session(
            database=settings.NEO4J_DATABASE,
            default_access_mode=READ_ACCESS,
        ) as session:
            yield session

    @asynccontextmanager
    async def write_session(self) -> AsyncIterator[AsyncSession]:
        if not self._driver:
            raise RuntimeError("Driver Neo4j não foi inicializado.")
        async with self._driver.session(
            database=settings.NEO4J_DATABASE,
            default_access_mode=WRITE_ACCESS,
        ) as session:
            yield session

    async def get_read_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.read_session() as session:
            yield session

    async def get_write_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.write_session() as session:
            yield session

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Compatibilidade temporária; novas leituras devem usar get_read_session."""
        async with self.read_session() as session:
            yield session


postgres_service = PostgresService()
neo4j_service = Neo4jService()
