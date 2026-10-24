import re
from pathlib import Path

import pytest

APP = Path(__file__).parents[2] / "app"
CYPHER = sorted(APP.rglob("*.cypher"))


def test_every_feed_ships_its_queries():
    assert {path.parent.name for path in CYPHER} >= {"professionals", "offers", "suppliers", "feeds"}
    assert not list(APP.rglob("*.sql"))


@pytest.mark.parametrize("path", CYPHER, ids=lambda path: f"{path.parent.name}/{path.name}")
def test_cypher_queries_only_read_the_active_snapshot(path):
    text = path.read_text(encoding="utf-8")

    assert "$source" in text
    assert not re.search(r"(CREATE|MERGE|DELETE|SET|REMOVE|DETACH)", text)
    if path.name != "active_version.cypher":
        assert "$sync_version" in text
