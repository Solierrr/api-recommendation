import re
from pathlib import Path

import pytest

APP = Path(__file__).parents[2] / "app"
CYPHER = sorted(APP.rglob("*.cypher"))
SQL = sorted(APP.rglob("*.sql"))

CORE_TABLES = {
    "certification",
    "company",
    "inventory",
    "model",
    "offer",
    "person",
    "profession",
    "professional_registration",
    "professional_review",
    "proposal",
    "proposal_item",
    "service_executor",
    "subscription",
    "supplier",
    "technical_service",
    "technician",
    "technician_affiliation",
    "users",
}


def test_every_feed_ships_its_queries():
    assert len(SQL) == 3
    assert {path.parent.name for path in CYPHER} >= {"professionals", "offers", "suppliers", "feeds"}


@pytest.mark.parametrize("path", CYPHER, ids=lambda path: f"{path.parent.name}/{path.name}")
def test_cypher_queries_only_read_the_active_snapshot(path):
    text = path.read_text(encoding="utf-8")

    assert "$source" in text
    assert not re.search(r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DETACH)\b", text)
    if path.name != "active_version.cypher":
        assert "$sync_version" in text


@pytest.mark.parametrize("path", SQL, ids=lambda path: path.parent.name)
def test_fallback_sql_samples_a_top_pool_with_two_parameters(path):
    text = path.read_text(encoding="utf-8")

    assert "LIMIT $1" in text
    assert "ORDER BY random()" in text
    assert "LIMIT $2" in text
    assert not re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b", text, re.IGNORECASE)


@pytest.mark.parametrize("path", SQL, ids=lambda path: path.parent.name)
def test_fallback_sql_uses_only_core_tables_or_its_own_ctes(path):
    text = path.read_text(encoding="utf-8")
    referenced = {match.group(1) for match in re.finditer(r"\b(?:FROM|JOIN)\s+([a-z_]+)", text)}
    ctes = {match.group(1) for match in re.finditer(r"\b([a-z_]+)\s+AS\s+\(", text)}

    assert referenced <= CORE_TABLES | ctes, referenced - CORE_TABLES - ctes


def test_the_professionals_fallback_accepts_an_optional_profession_filter():
    text = (APP / "feeds" / "professionals" / "fallback.sql").read_text(encoding="utf-8")

    assert "$3::uuid IS NULL" in text
