"""Test doubles assíncronos para Neo4j e PostgreSQL."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any


class FakeResult:
    def __init__(self, single_return: dict | None = None, data_return: list[dict] | None = None):
        self._single_return = single_return
        self._data_return = data_return or []

    async def single(self):
        return self._single_return

    async def data(self):
        return self._data_return


class FakeSession:
    def __init__(self, handler: Callable[[str, dict], FakeResult]):
        self.handler = handler
        self.calls: list[tuple[str, dict]] = []

    async def run(self, query: str, **parameters: Any) -> FakeResult:
        self.calls.append((query, parameters))
        return self.handler(query, parameters)


class FakeGraph:
    """Substitui GraphService: devolve uma sessão falsa ou levanta o erro configurado."""

    def __init__(
        self, handler: Callable[[str, dict], FakeResult] | None = None, error: Exception | None = None
    ):
        self.configured = True
        self.handler = handler
        self.error = error
        self.session: FakeSession | None = None

    @asynccontextmanager
    async def read_session(self) -> AsyncIterator[FakeSession]:
        if self.error is not None:
            raise self.error
        assert self.handler is not None
        self.session = FakeSession(self.handler)
        yield self.session


class FakeConnection:
    def __init__(self, rows: list[dict] | None = None, error: Exception | None = None):
        self.rows = rows or []
        self.error = error
        self.calls: list[tuple[str, tuple]] = []

    async def fetch(self, query: str, *parameters: Any) -> list[dict]:
        self.calls.append((query, parameters))
        if self.error is not None:
            raise self.error
        return self.rows

    async def fetchval(self, query: str) -> int:
        self.calls.append((query, ()))
        if self.error is not None:
            raise self.error
        return 1


class FakePostgres:
    def __init__(self, rows: list[dict] | None = None, error: Exception | None = None):
        self.connection_instance = FakeConnection(rows, error)

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[FakeConnection]:
        yield self.connection_instance
