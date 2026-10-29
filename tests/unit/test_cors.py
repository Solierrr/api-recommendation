from app.config import Settings
from tests.factories import offer
from tests.unit.test_feeds_api import graph_with

ORIGIN = "http://localhost:5173"


def preflight(client, path, origin=ORIGIN, headers="content-type"):
    return client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": headers,
        },
    )


def test_public_feed_preflight_is_answered_for_an_allowed_origin(client):
    response = preflight(client, "/public/feeds/offers")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "access-control-allow-credentials" not in response.headers


def test_public_feed_response_carries_the_allowed_origin_and_keeps_the_cache_headers(client, wired):
    graph_with(wired, [offer(1)])

    response = client.get("/public/feeds/offers", headers={"Origin": ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "Origin" in response.headers["vary"]
    assert response.headers["cache-control"] == "public, max-age=300, stale-if-error=86400"


def test_unknown_origin_gets_no_cors_headers(client):
    response = preflight(client, "/public/feeds/offers", origin="https://evil.example.com")

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_the_recommendation_key_header_is_not_allowed_from_the_browser(client):
    response = preflight(client, "/feeds/offers", headers="x-recommendation-key")

    assert response.status_code == 400
    assert "x-recommendation-key" not in response.headers["access-control-allow-headers"].lower()


def test_origins_come_from_a_comma_separated_list():
    settings = Settings(CORS_ALLOWED_ORIGINS=" https://a.com ,, https://b.com,")

    assert settings.cors_origins == ["https://a.com", "https://b.com"]
    assert Settings(CORS_ALLOWED_ORIGINS="").cors_origins == []


def test_default_origins_are_local_only():
    assert Settings().cors_origins == ["http://localhost:5173", "http://localhost:3000"]
