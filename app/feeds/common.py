import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from math import asin, cos, radians, sin, sqrt
from typing import Any
from uuid import UUID

from fastapi import Response
from pydantic import BaseModel, Field

from app.config import settings
from app.errors import FeedDataUnavailableError, GraphUnavailableError

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0088


class FeedSource(StrEnum):
    GRAPH = "graph"
    FALLBACK = "fallback"


class FeedContext(BaseModel):
    feed: str
    strategy: str | None
    company_id: UUID | None
    generated_at: datetime
    sync_version: UUID | None


class FeedResponse[ItemT: BaseModel](BaseModel):
    source: FeedSource
    context: FeedContext
    items: list[ItemT]
    warnings: list[str] = Field(default_factory=list)


class PublicFeedResponse[ItemT: BaseModel](BaseModel):
    source: FeedSource
    generated_at: datetime
    items: list[ItemT]


@dataclass(frozen=True)
class Rule:
    key: Callable[[dict], tuple]
    metric: Callable[[dict], float]
    unit: str
    reason: Callable[[dict], str]


@dataclass(frozen=True)
class FeedResult:
    source: FeedSource
    sync_version: str | None
    items: list[dict]
    warnings: list[str]


def now() -> datetime:
    return datetime.now(UTC)


def haversine_km(
    origin_latitude: float,
    origin_longitude: float,
    target_latitude: float,
    target_longitude: float,
) -> float:
    latitude_delta = radians(target_latitude - origin_latitude)
    longitude_delta = radians(target_longitude - origin_longitude)
    haversine = sin(latitude_delta / 2) ** 2 + (
        cos(radians(origin_latitude)) * cos(radians(target_latitude)) * sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * asin(sqrt(haversine))


def normalized(value: float, maximum: float) -> float:
    if maximum <= 0:
        return 0.0
    return max(0.0, min(value / maximum, 1.0))


def ranked(candidates: list[dict], rule: Rule, limit: int) -> list[dict]:
    ordered = sorted(candidates, key=rule.key)[:limit]
    return [
        {
            **candidate,
            "rank": position,
            "ranking_value": round(float(rule.metric(candidate)), 4),
            "ranking_unit": rule.unit,
            "reasons": [rule.reason(candidate)],
        }
        for position, candidate in enumerate(ordered, start=1)
    ]


def require_point(context: dict, missing_code: str, ambiguous_code: str, subject: str) -> None:
    count = context["geolocation_count"]
    if count == 0:
        raise FeedDataUnavailableError(
            missing_code, f"{subject} precisa de uma geolocalização para calcular distância."
        )
    if count > 1:
        raise FeedDataUnavailableError(
            ambiguous_code,
            f"{subject} possui mais de uma geolocalização; regularize o cadastro antes de calcular distância.",
        )


def bounded(candidates: list[dict], pool_limit: int) -> list[dict]:
    if len(candidates) > pool_limit:
        raise FeedDataUnavailableError(
            "CANDIDATE_POOL_TOO_LARGE",
            "O conjunto elegível excede o limite seguro para ranking global; "
            "refine o contexto ou aumente o limite operacional.",
        )
    return candidates


async def graph_or_fallback(
    graph_call: Callable[[], Awaitable[FeedResult]],
    fallback_call: Callable[[], Awaitable[list[dict]]],
    fallback_warning: str,
) -> FeedResult:
    try:
        return await graph_call()
    except GraphUnavailableError as error:
        logger.warning("Feed servido pelo fallback SQL: %s", error)
    items = await fallback_call()
    return FeedResult(FeedSource.FALLBACK, None, items, [fallback_warning])


COMPANY_WARNING = "company_id foi recebido, mas a personalização por empresa ainda não influencia o ranking."


def build_response(
    feed: str, strategy: str | None, company_id: UUID | None, result: FeedResult
) -> dict[str, Any]:
    warnings = [*result.warnings, COMPANY_WARNING] if company_id is not None else list(result.warnings)
    return {
        "source": result.source,
        "context": {
            "feed": feed,
            "strategy": strategy,
            "company_id": company_id,
            "generated_at": now(),
            "sync_version": result.sync_version,
        },
        "items": result.items,
        "warnings": warnings,
    }


def build_public_response(items: list[dict]) -> dict[str, Any]:
    return {"source": FeedSource.FALLBACK, "generated_at": now(), "items": items}


def set_public_cache(response: Response) -> None:
    response.headers["Cache-Control"] = (
        f"public, max-age={settings.PUBLIC_CACHE_SECONDS}, "
        f"stale-if-error={settings.PUBLIC_STALE_IF_ERROR_SECONDS}"
    )
