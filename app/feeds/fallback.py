import logging
from pathlib import Path
from typing import Any

import asyncpg

from app.database import PostgresService
from app.errors import FeedUnavailableError
from app.queries import load

logger = logging.getLogger(__name__)


async def sample(postgres: PostgresService, query_file: Path, *parameters: Any) -> list[dict]:
    try:
        async with postgres.connection() as connection:
            rows = await connection.fetch(load(query_file), *parameters)
    except (asyncpg.PostgresError, OSError, TimeoutError, RuntimeError) as error:
        logger.exception("Falha no fallback SQL")
        raise FeedUnavailableError(
            "FEED_UNAVAILABLE", "Não foi possível obter o feed nem pelo grafo nem pelo banco."
        ) from error
    return [dict(row) for row in rows]


def decorate(rows: list[dict], unit: str, reason: str, value_field: str) -> list[dict]:
    return [
        {
            **row,
            "rank": position,
            "ranking_value": float(row.get(value_field) or 0.0),
            "ranking_unit": unit,
            "reasons": [reason],
        }
        for position, row in enumerate(rows, start=1)
    ]
