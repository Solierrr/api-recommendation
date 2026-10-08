import asyncpg
import pytest

from app.errors import GraphUnavailableError
from tests.factories import (
    COMPANY_ID,
    LOCAL_UNIT,
    PROFESSION_ID,
    UNIT_ID,
    VERSION,
    fallback_offer,
    fallback_professional,
    fallback_supplier,
    graph_handler,
    offer,
    professional,
    supplier,
    uuid,
)
from tests.fakes import FakeGraph, FakePostgres

FEEDS = ("professionals", "offers", "suppliers")


def graph_with(wired, candidates, **kwargs):
    graph, _ = wired
    graph.handler = graph_handler(candidates, **kwargs)
    return graph


def test_professionals_feed_ranks_graph_candidates(client, wired):
    graph_with(
        wired, [professional(1, average_rating_global=3.0), professional(2, average_rating_global=5.0)]
    )

    response = client.get(
        "/feeds/professionals",
        params={"strategy": "top_rated", "profession_id": PROFESSION_ID, "company_id": COMPANY_ID},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["source"] == "graph"
    assert body["context"]["feed"] == "professionals"
    assert body["context"]["strategy"] == "top_rated"
    assert body["context"]["company_id"] == COMPANY_ID
    assert body["context"]["sync_version"] == VERSION
    assert [item["technician_id"] for item in body["items"]] == [uuid(2), uuid(1)]
    assert body["items"][0]["rank"] == 1
    assert any("company_id" in warning for warning in body["warnings"])


def test_professionals_feed_filters_candidates_by_the_requested_profession(client, wired):
    graph = graph_with(wired, [professional(1)])

    client.get("/feeds/professionals", params={"profession_id": PROFESSION_ID})

    candidate_call = next(call for call in graph.session.calls if "fetch_limit" in call[0])
    assert candidate_call[1]["profession_id"] == PROFESSION_ID
    assert candidate_call[1]["sync_version"] == VERSION
    assert candidate_call[1]["fetch_limit"] == 501


def test_professionals_feed_reports_an_unknown_profession(client, wired):
    def handler(query, parameters):
        result = graph_handler([])(query, parameters)
        if "RETURN profession.id AS id" in query:
            result._single_return = None
        return result

    wired[0].handler = handler

    response = client.get("/feeds/professionals", params={"profession_id": PROFESSION_ID})

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PROFESSION_NOT_FOUND"


def test_offers_feed_ranks_graph_candidates(client, wired):
    graph_with(wired, [offer(1, unit_price_cents=50000), offer(2, unit_price_cents=30000)])

    response = client.get("/feeds/offers", params={"strategy": "best_value", "local_unit_id": UNIT_ID})

    body = response.json()
    assert response.status_code == 200
    assert body["source"] == "graph"
    assert [item["offer_id"] for item in body["items"]] == [uuid(202), uuid(201)]
    assert body["items"][0]["unit_price"] == 300.0
    assert body["items"][0]["ranking_unit"] == "BRL_per_Wp"


def test_offers_feed_reports_an_unknown_local_unit(client, wired):
    graph_with(wired, [offer(1)], local_unit=None)

    response = client.get("/feeds/offers", params={"local_unit_id": UNIT_ID})

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "LOCAL_UNIT_NOT_FOUND"


@pytest.mark.parametrize("feed", ["offers", "suppliers"])
def test_nearest_strategies_require_a_local_unit(client, wired, feed):
    candidates = [offer(1)] if feed == "offers" else [supplier(1)]
    graph_with(wired, candidates)
    strategy = "nearest_available" if feed == "offers" else "nearest"

    response = client.get(f"/feeds/{feed}", params={"strategy": strategy})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "LOCAL_UNIT_REQUIRED"


def test_suppliers_feed_ranks_graph_candidates(client, wired):
    graph_with(
        wired,
        [supplier(1, accepted_proposal_quantity=1), supplier(2, accepted_proposal_quantity=7)],
        local_unit=LOCAL_UNIT,
    )

    response = client.get("/feeds/suppliers")

    body = response.json()
    assert response.status_code == 200
    assert body["context"]["strategy"] == "most_proven"
    assert [item["supplier_id"] for item in body["items"]] == [uuid(302), uuid(301)]


def test_a_candidate_pool_above_the_limit_is_refused(client, wired, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "RECOMMENDATION_POOL_LIMIT", 10)
    graph_with(wired, [offer(number) for number in range(11)])

    response = client.get("/feeds/offers")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CANDIDATE_POOL_TOO_LARGE"


@pytest.mark.parametrize(
    ("feed", "rows"),
    [
        ("professionals", [fallback_professional(1), fallback_professional(2)]),
        ("offers", [fallback_offer(1), fallback_offer(2)]),
        ("suppliers", [fallback_supplier(1), fallback_supplier(2)]),
    ],
)
@pytest.mark.parametrize(
    "error",
    [GraphUnavailableError("sem conexão"), GraphUnavailableError("Neo4j não configurado")],
    ids=["graph-down", "graph-not-configured"],
)
def test_feeds_fall_back_to_sql_when_the_graph_is_unavailable(client, feed, rows, error):
    from app.dependencies import get_graph, get_postgres
    from app.main import app

    graph = FakeGraph(error=error)
    postgres = FakePostgres(rows=rows)
    app.dependency_overrides[get_graph] = lambda: graph
    app.dependency_overrides[get_postgres] = lambda: postgres
    try:
        response = client.get(f"/feeds/{feed}")
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["source"] == "fallback"
    assert body["context"]["sync_version"] is None
    assert [item["rank"] for item in body["items"]] == [1, 2]
    assert all(item["reasons"] for item in body["items"])
    assert any("indisponível" in warning for warning in body["warnings"])
    parameters = postgres.connection_instance.calls[0][1]
    assert parameters[:2] == (30, 10)


def test_professionals_fallback_passes_the_profession_filter(client):
    from app.dependencies import get_graph, get_postgres
    from app.main import app

    postgres = FakePostgres(rows=[fallback_professional(1)])
    app.dependency_overrides[get_graph] = lambda: FakeGraph(error=GraphUnavailableError("x"))
    app.dependency_overrides[get_postgres] = lambda: postgres
    try:
        response = client.get("/feeds/professionals", params={"profession_id": PROFESSION_ID})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert str(postgres.connection_instance.calls[0][1][2]) == PROFESSION_ID


def test_a_missing_snapshot_also_falls_back(client, wired):
    from app.errors import SnapshotUnavailableError

    graph, postgres = wired
    graph.error = SnapshotUnavailableError("sem snapshot")
    postgres.connection_instance.rows = [fallback_offer(1)]

    response = client.get("/feeds/offers")

    assert response.status_code == 200
    assert response.json()["source"] == "fallback"


def test_feeds_answer_503_when_neither_the_graph_nor_the_database_respond(client):
    from app.dependencies import get_graph, get_postgres
    from app.main import app

    app.dependency_overrides[get_graph] = lambda: FakeGraph(error=GraphUnavailableError("x"))
    app.dependency_overrides[get_postgres] = lambda: FakePostgres(error=asyncpg.PostgresError("fora"))
    try:
        response = client.get("/feeds/suppliers")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "FEED_UNAVAILABLE"


def test_unexpected_errors_become_a_generic_500(client, wired):
    graph, _ = wired
    graph.handler = lambda query, parameters: (_ for _ in ()).throw(ValueError("segredo interno"))

    response = client.get("/feeds/offers")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "RECOMMENDATION_FAILED"
    assert "segredo" not in response.text


@pytest.mark.parametrize(
    ("feed", "rows", "private_fields"),
    [
        (
            "professionals",
            [fallback_professional(1)],
            {"rank", "ranking_value", "assigned_service_count_global"},
        ),
        ("offers", [fallback_offer(1)], {"rank", "ranking_value", "accepted_proposal_quantity", "model_id"}),
        ("suppliers", [fallback_supplier(1)], {"rank", "ranking_value", "company_id"}),
    ],
)
def test_public_feeds_use_sql_only_with_cache_headers_and_a_sanitized_shape(
    client, graph, postgres, feed, rows, private_fields
):
    from app.dependencies import get_graph, get_postgres
    from app.main import app

    postgres.connection_instance.rows = rows
    app.dependency_overrides[get_graph] = lambda: graph
    app.dependency_overrides[get_postgres] = lambda: postgres
    try:
        response = client.get(f"/public/feeds/{feed}")
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["source"] == "fallback"
    assert len(body["items"]) == 1
    assert private_fields.isdisjoint(body["items"][0])
    assert response.headers["cache-control"] == "public, max-age=300, stale-if-error=86400"
    assert graph.session is None


def test_public_feeds_do_not_need_the_recommendation_key(client, wired, monkeypatch):
    from pydantic import SecretStr

    from app.config import settings

    monkeypatch.setattr(settings, "RECOMMENDATION_API_KEY", SecretStr("k" * 40))
    wired[1].connection_instance.rows = [fallback_offer(1)]

    public = client.get("/public/feeds/offers")
    private = client.get("/feeds/offers")

    assert public.status_code == 200
    assert private.status_code == 401


def test_the_openapi_document_lists_the_three_feeds_and_their_public_variants(client):
    paths = client.get("/openapi.json").json()["paths"]

    for feed in FEEDS:
        assert f"/feeds/{feed}" in paths
        assert f"/public/feeds/{feed}" in paths
    assert not any(
        path.startswith(("/recommendations", "/candidates", "/events", "/internal")) for path in paths
    )
