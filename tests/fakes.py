"""Test doubles simples para simular o driver assíncrono do Neo4j nos testes
unitários, sem depender de uma conexão real com o banco de dados.
"""

from collections.abc import Callable


class FakeResult:
    """Simula o objeto Result retornado por `AsyncSession.run()`."""

    def __init__(self, single_return=None, data_return=None):
        self._single_return = single_return
        self._data_return = data_return if data_return is not None else []

    async def single(self):
        return self._single_return

    async def data(self):
        return self._data_return


class FakeSession:
    """Simula uma AsyncSession do driver neo4j.

    `result_factory`, quando fornecido, recebe (query, params) e deve
    devolver um FakeResult (ou lançar uma exceção, para simular falhas de
    conexão/query). Tem prioridade sobre `result`.
    """

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
