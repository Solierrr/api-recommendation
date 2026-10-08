import pytest

from app.errors import ContextNotFoundError, FeedDataUnavailableError, SnapshotUnavailableError
from app.feeds.offers.service import OffersService
from app.feeds.offers.strategies import OfferStrategy
from app.feeds.professionals.service import ProfessionalsService
from app.feeds.professionals.strategies import ProfessionalStrategy
from app.feeds.suppliers.service import SuppliersService
from app.feeds.suppliers.strategies import SupplierStrategy
from tests.fakes import FakePostgres
from tests.integration import graph_seed as seed
from tests.integration.conftest import needs_neo4j

pytestmark = needs_neo4j


def ids(result, field):
    return [item[field] for item in result.items]


async def test_professionals_come_only_from_the_active_snapshot_and_active_users(seeded_graph):
    service = ProfessionalsService(seeded_graph, FakePostgres())

    result = await service.recommend(ProfessionalStrategy.TOP_RATED, None)

    assert result.source == "graph"
    assert result.sync_version == seed.VERSION
    assert ids(result, "technician_id") == [seed.TECHNICIAN]
    item = result.items[0]
    assert sorted(item["professions"]) == ["Engenheiro Eletricista", "Instalador"]
    assert item["valid_certification_count"] == 2
    assert item["certification_names"] == ["NR-10", "NR-35"]
    assert item["average_rating_global"] == 4.5


async def test_professionals_can_be_filtered_by_profession(seeded_graph):
    service = ProfessionalsService(seeded_graph, FakePostgres())

    result = await service.recommend(ProfessionalStrategy.BEST_MATCH, seed_uuid(seed.PROFESSION))

    assert ids(result, "technician_id") == [seed.TECHNICIAN]
    assert result.items[0]["professions"] == ["Engenheiro Eletricista"]
    assert result.items[0]["valid_certification_count"] == 1


async def test_an_unknown_profession_is_a_not_found_error(seeded_graph):
    service = ProfessionalsService(seeded_graph, FakePostgres())

    with pytest.raises(ContextNotFoundError) as error:
        await service.recommend(
            ProfessionalStrategy.TOP_RATED, seed_uuid("00000000-0000-4000-8000-0000000000ff")
        )

    assert error.value.code == "PROFESSION_NOT_FOUND"


async def test_offers_exclude_rejected_models_and_suspended_suppliers(seeded_graph):
    service = OffersService(seeded_graph, FakePostgres())

    result = await service.recommend(OfferStrategy.MOST_PROVEN, None)

    assert ids(result, "offer_id") == [seed.FAR_OFFER, seed.OFFER]
    assert result.items[0]["supplier_trade_name"] == "Sol Distante"
    assert result.items[1]["unit_price"] == 750.55
    assert result.items[1]["accepted_proposal_quantity"] == 3


async def test_nearest_offers_are_ordered_by_distance_from_the_unit(seeded_graph):
    service = OffersService(seeded_graph, FakePostgres())

    result = await service.recommend(OfferStrategy.NEAREST_AVAILABLE, seed_uuid(seed.UNIT))

    assert ids(result, "offer_id") == [seed.OFFER, seed.FAR_OFFER]
    assert result.items[0]["distance_km"] < result.items[1]["distance_km"]
    assert result.items[0]["distance_km"] == pytest.approx(111.195, abs=0.01)


async def test_an_unknown_local_unit_is_a_not_found_error(seeded_graph):
    service = OffersService(seeded_graph, FakePostgres())

    with pytest.raises(ContextNotFoundError) as error:
        await service.recommend(OfferStrategy.BEST_VALUE, seed_uuid("00000000-0000-4000-8000-0000000000fe"))

    assert error.value.code == "LOCAL_UNIT_NOT_FOUND"


async def test_nearest_offers_without_a_unit_are_refused(seeded_graph):
    service = OffersService(seeded_graph, FakePostgres())

    with pytest.raises(FeedDataUnavailableError) as error:
        await service.recommend(OfferStrategy.NEAREST_AVAILABLE, None)

    assert error.value.code == "LOCAL_UNIT_REQUIRED"


async def test_suppliers_are_aggregated_from_their_eligible_offers(seeded_graph):
    service = SuppliersService(seeded_graph, FakePostgres())

    result = await service.recommend(SupplierStrategy.MOST_PROVEN, None)

    assert ids(result, "supplier_id") == [seed.FAR_SUPPLIER, seed.SUPPLIER]
    far, near = result.items
    assert (far["offer_count"], far["accepted_proposal_quantity"]) == (1, 9)
    assert (near["offer_count"], near["accepted_proposal_quantity"]) == (1, 3)
    assert near["trade_name"] == "Solar Forte"


async def test_nearest_suppliers_use_the_unit_location(seeded_graph):
    service = SuppliersService(seeded_graph, FakePostgres())

    result = await service.recommend(SupplierStrategy.NEAREST, seed_uuid(seed.UNIT))

    assert ids(result, "supplier_id") == [seed.SUPPLIER, seed.FAR_SUPPLIER]


async def test_without_a_snapshot_the_graph_reports_it_is_unavailable(empty_graph):
    service = OffersService(empty_graph, FakePostgres(rows=[]))

    with pytest.raises(SnapshotUnavailableError):
        async with empty_graph.read_session() as session:
            from app.feeds import graph

            await graph.active_snapshot(session)

    result = await service.recommend(OfferStrategy.BEST_VALUE, None)
    assert result.source == "fallback"


async def test_the_active_snapshot_reports_its_version_and_age(seeded_graph):
    from app.feeds import graph

    async with seeded_graph.read_session() as session:
        snapshot = await graph.active_snapshot(session)

    assert snapshot["active_version"] == seed.VERSION
    assert 0 <= snapshot["snapshot_age_seconds"] < 60


def seed_uuid(value: str):
    from uuid import UUID

    return UUID(value)
