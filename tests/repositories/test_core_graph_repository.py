import pytest

from app.repositories.core_graph_repository import (
    CoreGraphRepository,
    CoreGraphSnapshot,
)


def empty_snapshot(**overrides) -> CoreGraphSnapshot:
    values = {
        "local_units": [],
        "panel_offers": [],
        "professions": [],
        "professionals": [],
        "affiliations": [],
        "shifts": [],
        "technical_services": [],
        "service_experiences": [],
        "assignments": [],
    }
    values.update(overrides)
    return CoreGraphSnapshot(**values)


def valid_panel_row(**overrides) -> dict:
    row = {
        "model_id": "model-1",
        "brand": "Sol",
        "model": "X1",
        "power_wp": 500.0,
        "efficiency": 20.0,
        "dimension": 2.0,
        "weight": 25.0,
        "model_status": "APPROVED",
        "offer_id": "offer-1",
        "unit_price_cents": 100_000,
        "availability": 10,
        "expiration_at": None,
        "inventory_quantity": 10,
        "effective_availability": 10,
        "supplier_id": "supplier-1",
        "supplier_status": "ACTIVE",
        "business_type": "INSTALLER",
        "company_id": "company-1",
        "trade_name": "Solar",
        "subscription_active": True,
        "accepted_proposal_quantity": 3,
        "supplier_geolocation_count": 0,
        "supplier_latitude": None,
        "supplier_longitude": None,
    }
    row.update(overrides)
    return row


def test_profession_exists_in_snapshot_without_eligible_professional() -> None:
    snapshot = empty_snapshot(
        professions=[
            {
                "profession_id": "profession-1",
                "profession_name": "Eletricista",
                "requires_registration": True,
                "accept_emergency_call": False,
            }
        ]
    )

    assert snapshot.expected_node_counts["professions"] == 1
    assert snapshot.counts["professions"] == 1
    assert snapshot.counts["professionals"] == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("power_wp", 0),
        ("power_wp", float("nan")),
        ("efficiency", 101),
        ("dimension", -1),
        ("weight", float("inf")),
    ],
)
def test_invalid_panel_numeric_data_is_filtered(field, value) -> None:
    assert CoreGraphRepository._panel_offer(valid_panel_row(**{field: value})) is None


def test_most_proven_uses_proposal_item_quantity() -> None:
    query = CoreGraphRepository.FIND_PANEL_OFFERS

    assert "SUM(proposal_item.quantity)" in query
    assert "FROM proposal_unit" not in query


@pytest.mark.asyncio
async def test_snapshot_loader_renews_lease_after_every_source_query() -> None:
    class EmptyConnection:
        def __init__(self):
            self.queries = []

        async def fetch(self, query):
            self.queries.append(query)
            return []

    connection = EmptyConnection()
    heartbeat_count = 0

    async def heartbeat():
        nonlocal heartbeat_count
        heartbeat_count += 1

    snapshot = await CoreGraphRepository.load_snapshot(connection, heartbeat)

    assert snapshot.expected_node_count == 0
    assert heartbeat_count == len(connection.queries) == 9


def test_inactive_affiliation_assignments_keep_technician_identity_in_graph() -> None:
    assert "technician_affiliation.active IS TRUE" not in (
        CoreGraphRepository.FIND_AFFILIATIONS
    )
    assert "technician_affiliation.active IS TRUE" not in (
        CoreGraphRepository.FIND_ASSIGNMENTS
    )
    assert "WHERE users.active IS TRUE" in CoreGraphRepository.FIND_ASSIGNMENTS
