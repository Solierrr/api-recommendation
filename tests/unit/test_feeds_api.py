import pytest

from app.errors import GraphUnavailableError, SnapshotUnavailableError
from tests.factories import (
    COMPANY_ID,
    LOCAL_UNIT,
    PROFESSION_ID,
    UNIT_ID,
    VERSION,
    graph_handler,
    offer,
    professional,
    supplier,
    uuid,
)

FEEDS = ("professionals", "offers", "suppliers")


def graph_with(graph, candidates, **kwargs):
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

    wired.handler = handler

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
    "path", [f"/{prefix}/{feed}" for prefix in ("feeds", "public/feeds") for feed in FEEDS]
)
@pytest.mark.parametrize(
    "error",
    [
        GraphUnavailableError("sem conexão"),
        GraphUnavailableError("Neo4j não configurado"),
        SnapshotUnavailableError("sem snapshot"),
    ],
    ids=["graph-down", "graph-not-configured", "no-snapshot"],
)
def test_feeds_answer_503_when_the_graph_is_unavailable(client, wired, path, error):
    wired.error = error

    response = client.get(path)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "FEED_UNAVAILABLE"
    assert "sem conexão" not in response.text


def test_unexpected_errors_become_a_generic_500(client, wired):
    wired.handler = lambda query, parameters: (_ for _ in ()).throw(ValueError("segredo interno"))

    response = client.get("/feeds/offers")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "RECOMMENDATION_FAILED"
    assert "segredo" not in response.text


@pytest.mark.parametrize(
    ("feed", "candidates", "private_fields"),
    [
        (
            "professionals",
            [professional(1)],
            {"rank", "ranking_value", "assigned_service_count_global"},
        ),
        ("offers", [offer(1)], {"rank", "ranking_value", "accepted_proposal_quantity", "model_id"}),
        ("suppliers", [supplier(1)], {"rank", "ranking_value", "company_id"}),
    ],
)
def test_public_feeds_are_served_from_the_graph_with_cache_headers_and_a_sanitized_shape(
    client, wired, feed, candidates, private_fields
):
    graph_with(wired, candidates)

    response = client.get(f"/public/feeds/{feed}")

    body = response.json()
    assert response.status_code == 200
    assert body["source"] == "graph"
    assert len(body["items"]) == 1
    assert private_fields.isdisjoint(body["items"][0])
    assert response.headers["cache-control"] == "public, max-age=300, stale-if-error=86400"
    assert wired.session is not None


def test_public_professionals_filter_by_the_requested_profession(client, wired):
    graph_with(wired, [professional(1)])

    response = client.get("/public/feeds/professionals", params={"profession_id": PROFESSION_ID})

    assert response.status_code == 200
    candidate_call = next(call for call in wired.session.calls if "fetch_limit" in call[0])
    assert candidate_call[1]["profession_id"] == PROFESSION_ID


def test_public_feeds_do_not_need_the_recommendation_key(client, wired, monkeypatch):
    from pydantic import SecretStr

    from app.config import settings

    monkeypatch.setattr(settings, "RECOMMENDATION_API_KEY", SecretStr("k" * 40))
    graph_with(wired, [offer(1)])

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
