from uuid import UUID

import pytest

from app.config import settings
from app.feeds.offers.service import OffersService
from app.feeds.professionals.service import ProfessionalsService
from app.feeds.suppliers.service import SuppliersService
from tests.integration.conftest import needs_postgres

pytestmark = needs_postgres

ELIGIBLE_TECHNICIAN = "00000000-0000-0000-0000-000000000171"
ENGINEER = UUID("00000000-0000-0000-0000-000000000181")
INSTALLER = UUID("00000000-0000-0000-0000-000000000182")


class NoGraph:
    configured = False


async def test_professionals_fallback_returns_only_eligible_technicians(seeded_postgres):
    service = ProfessionalsService(NoGraph(), seeded_postgres)  # type: ignore[arg-type]

    items = await service.public(None)

    assert [item["technician_id"] for item in items] == [ELIGIBLE_TECHNICIAN]
    item = items[0]
    assert item["name"].startswith("Profissional ")
    assert item["professions"] == ["Engenheiro Eletricista"]
    assert item["average_rating_global"] == 4.5
    assert item["review_count_global"] == 1
    assert item["assigned_service_count_global"] == 2
    assert item["completed_service_count_global"] == 1
    assert item["valid_certification_count"] == 1
    assert item["certification_names"] == ["NR-10"]


async def test_professionals_fallback_honours_the_profession_filter(seeded_postgres):
    service = ProfessionalsService(NoGraph(), seeded_postgres)  # type: ignore[arg-type]

    assert len(await service.public(ENGINEER)) == 1
    assert await service.public(INSTALLER) == []


async def test_offers_fallback_returns_only_eligible_offers_with_aggregated_stock(seeded_postgres):
    service = OffersService(NoGraph(), seeded_postgres)  # type: ignore[arg-type]

    items = await service.public()

    assert [item["offer_id"] for item in items] == ["00000000-0000-0000-0000-000000000101"]
    item = items[0]
    assert item["supplier_trade_name"] == "Solar Forte"
    assert item["brand"] == "Canadian"
    assert item["effective_availability"] == 15
    assert item["accepted_proposal_quantity"] == 3
    assert item["unit_price"] == pytest.approx(750.55)
    assert item["dimension"] == pytest.approx(2.53)
    assert item["ranking_unit"] == "BRL_per_Wp"


async def test_suppliers_fallback_returns_only_active_suppliers_with_eligible_offers(seeded_postgres):
    service = SuppliersService(NoGraph(), seeded_postgres)  # type: ignore[arg-type]

    items = await service.public()

    assert [item["supplier_id"] for item in items] == ["00000000-0000-0000-0000-0000000000d1"]
    assert items[0]["trade_name"] == "Solar Forte"
    assert items[0]["offer_count"] == 1
    assert items[0]["accepted_proposal_quantity"] == 3


async def test_the_sample_never_exceeds_the_configured_result_limit(seeded_postgres, monkeypatch):
    monkeypatch.setattr(settings, "RECOMMENDATION_RESULT_LIMIT", 1)
    service = ProfessionalsService(NoGraph(), seeded_postgres)  # type: ignore[arg-type]

    assert len(await service.public(None)) <= 1
