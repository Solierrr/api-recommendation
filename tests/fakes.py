"""Test doubles assíncronos para Neo4j e PostgreSQL."""

from collections.abc import Callable


class FakeResult:
    def __init__(self, single_return=None, data_return=None):
        self._single_return = single_return
        self._data_return = data_return if data_return is not None else []

    async def single(self):
        return self._single_return

    async def data(self):
        return self._data_return


class FakeSession:
    def __init__(
        self,
        result: FakeResult | None = None,
        result_factory: Callable | None = None,
    ):
        self._result = result
        self._result_factory = result_factory
        self.calls: list[tuple[str, dict]] = []

    async def run(self, query: str, **params):
        self.calls.append((query, params))
        if self._result_factory is not None:
            return self._result_factory(query, params)
        return self._result


class FakeConnection:
    def __init__(self, fetchval_return=1, error: Exception | None = None):
        self.fetchval_return = fetchval_return
        self.error = error
        self.calls: list[str] = []

    async def fetchval(self, query: str):
        self.calls.append(query)
        if self.error is not None:
            raise self.error
        return self.fetchval_return
