from uuid import UUID

import pytest
from fastapi import Response

from app.config import settings
from app.errors import FeedDataUnavailableError, GraphUnavailableError
from app.feeds.common import (
    FeedResult,
    FeedSource,
    Rule,
    bounded,
    build_public_response,
    build_response,
    graph_or_fallback,
    haversine_km,
    normalized,
    ranked,
    require_point,
    set_public_cache,
)

COMPANY = UUID("44444444-4444-4444-8444-444444444444")


def test_haversine_matches_a_known_distance():
    # Sao Paulo -> Rio de Janeiro fica a cerca de 360 km em linha reta.
    distance = haversine_km(-23.5505, -46.6333, -22.9068, -43.1729)

    assert distance == pytest.approx(360.7, abs=1.0)
    assert haversine_km(1.0, 1.0, 1.0, 1.0) == 0.0


@pytest.mark.parametrize(
    ("value", "maximum", "expected"),
    [(5, 10, 0.5), (20, 10, 1.0), (-1, 10, 0.0), (3, 0, 0.0), (3, -2, 0.0)],
)
def test_normalized_is_bounded_between_zero_and_one(value, maximum, expected):
    assert normalized(value, maximum) == expected


def test_ranked_orders_limits_and_annotates_without_mutating():
    rule = Rule(
        key=lambda item: (item["value"], item["id"]),
        metric=lambda item: item["value"],
        unit="points",
        reason=lambda item: f"valor {item['value']}",
    )
    candidates = [{"id": "b", "value": 2}, {"id": "a", "value": 1}, {"id": "c", "value": 3}]

    items = ranked(candidates, rule, limit=2)

    assert [item["id"] for item in items] == ["a", "b"]
    assert [item["rank"] for item in items] == [1, 2]
    assert items[0]["ranking_value"] == 1.0
    assert items[0]["ranking_unit"] == "points"
    assert items[0]["reasons"] == ["valor 1"]
    assert "rank" not in candidates[0]


@pytest.mark.parametrize(
    ("count", "code"),
    [(0, "UNIT_MISSING"), (2, "UNIT_AMBIGUOUS")],
)
def test_require_point_rejects_missing_or_ambiguous_locations(count, code):
    with pytest.raises(FeedDataUnavailableError) as error:
        require_point({"geolocation_count": count}, "UNIT_MISSING", "UNIT_AMBIGUOUS", "A unidade")

    assert error.value.code == code


def test_require_point_accepts_a_single_location():
    require_point({"geolocation_count": 1}, "UNIT_MISSING", "UNIT_AMBIGUOUS", "A unidade")


def test_bounded_refuses_pools_above_the_limit():
    assert bounded([1, 2, 3], 3) == [1, 2, 3]
    with pytest.raises(FeedDataUnavailableError) as error:
        bounded([1, 2, 3, 4], 3)

    assert error.value.code == "CANDIDATE_POOL_TOO_LARGE"


async def test_graph_or_fallback_prefers_the_graph():
    async def from_graph():
        return FeedResult(FeedSource.GRAPH, "v1", [{"id": 1}], [])

    async def from_sql():
        raise AssertionError("o fallback não deveria ser chamado")

    result = await graph_or_fallback(from_graph, from_sql, "aviso")

    assert result.source is FeedSource.GRAPH
    assert result.sync_version == "v1"


async def test_graph_or_fallback_uses_sql_when_the_graph_is_unavailable():
    async def from_graph():
        raise GraphUnavailableError("fora")

    async def from_sql():
        return [{"id": 9}]

    result = await graph_or_fallback(from_graph, from_sql, "aviso")

    assert result.source is FeedSource.FALLBACK
    assert result.sync_version is None
    assert result.items == [{"id": 9}]
    assert result.warnings == ["aviso"]


async def test_graph_or_fallback_does_not_hide_domain_errors():
    async def from_graph():
        raise FeedDataUnavailableError("CODE", "mensagem")

    async def from_sql():
        raise AssertionError("o fallback não deveria ser chamado")

    with pytest.raises(FeedDataUnavailableError):
        await graph_or_fallback(from_graph, from_sql, "aviso")


def test_build_response_adds_the_company_warning_only_when_a_company_is_sent():
    result = FeedResult(FeedSource.GRAPH, "v1", [], ["base"])

    with_company = build_response("offers", "best_value", COMPANY, result)
    without_company = build_response("offers", "best_value", None, result)

    assert with_company["context"]["company_id"] == COMPANY
    assert len(with_company["warnings"]) == 2
    assert without_company["warnings"] == ["base"]
    assert without_company["context"]["feed"] == "offers"


def test_public_response_is_always_marked_as_fallback():
    body = build_public_response([{"id": 1}])

    assert body["source"] is FeedSource.FALLBACK
    assert body["items"] == [{"id": 1}]


def test_public_cache_header_comes_from_the_settings(monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_CACHE_SECONDS", 60)
    monkeypatch.setattr(settings, "PUBLIC_STALE_IF_ERROR_SECONDS", 120)
    response = Response()

    set_public_cache(response)

    assert response.headers["cache-control"] == "public, max-age=60, stale-if-error=120"
