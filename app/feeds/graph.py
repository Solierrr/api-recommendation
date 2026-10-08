from pathlib import Path
from typing import Any

from neo4j import AsyncSession

from app.errors import ContextNotFoundError, SnapshotUnavailableError
from app.queries import load

SOURCE = "api-core"

_DIRECTORY = Path(__file__).parent


def native(value: Any) -> Any:
    if hasattr(value, "to_native"):
        return value.to_native()
    if isinstance(value, list):
        return [native(item) for item in value]
    if isinstance(value, dict):
        return {key: native(item) for key, item in value.items()}
    return value


async def fetch_one(session: AsyncSession, query: str, **parameters: Any) -> dict | None:
    result = await session.run(query, source=SOURCE, **parameters)
    record = await result.single()
    return native(dict(record)) if record else None


async def fetch_all(session: AsyncSession, query: str, **parameters: Any) -> list[dict]:
    result = await session.run(query, source=SOURCE, **parameters)
    return [native(dict(row)) for row in await result.data()]


async def active_snapshot(session: AsyncSession) -> dict:
    snapshot = await fetch_one(session, load(_DIRECTORY / "active_version.cypher"))
    if snapshot is None:
        raise SnapshotUnavailableError("Nenhum snapshot de recomendação está ativo")
    return snapshot


async def local_unit_context(session: AsyncSession, version: str, local_unit_id: str) -> dict:
    context = await fetch_one(
        session,
        load(_DIRECTORY / "local_unit.cypher"),
        sync_version=version,
        context_id=local_unit_id,
    )
    if context is None:
        raise ContextNotFoundError("LOCAL_UNIT_NOT_FOUND", "A unidade local não existe no snapshot ativo.")
    return context
