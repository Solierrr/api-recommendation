import pytest

from app.errors import FeedDataUnavailableError
from app.feeds.offers.strategies import OfferStrategy, rank_offers
from app.feeds.professionals.strategies import ProfessionalStrategy, rank_professionals
from app.feeds.suppliers.strategies import SupplierStrategy, rank_suppliers
from tests.factories import LOCAL_UNIT, offer, professional, supplier, uuid


def order(items: list[dict], field: str) -> list[str]:
    return [item[field] for item in items]


@pytest.fixture
def professionals():
    return [
        professional(
            1,
            average_rating_global=4.5,
            review_count_global=10,
            completed_service_count_global=8,
            canceled_service_count_global=0,
            valid_certification_count=2,
        ),
        professional(
            2,
            average_rating_global=5.0,
            review_count_global=1,
            completed_service_count_global=1,
            canceled_service_count_global=0,
            valid_certification_count=0,
        ),
        professional(
            3,
            average_rating_global=3.0,
            review_count_global=20,
            completed_service_count_global=30,
            canceled_service_count_global=10,
            valid_certification_count=1,
        ),
    ]


@pytest.mark.parametrize(
    ("strategy", "expected", "unit"),
    [
        (ProfessionalStrategy.TOP_RATED, [1, 2, 3], "bayesian_rating_0_5"),
        (ProfessionalStrategy.MOST_QUALIFIED, [1, 3, 2], "valid_certification_count"),
        (ProfessionalStrategy.MOST_EXPERIENCED, [3, 1, 2], "completed_service_count_global"),
        (ProfessionalStrategy.MOST_RELIABLE, [1, 2, 3], "reliability_score_0_1"),
        (ProfessionalStrategy.BEST_MATCH, [1, 3, 2], "best_match_score_0_1"),
    ],
)
def test_professionals_are_ranked_by_each_strategy(professionals, strategy, expected, unit):
    items = rank_professionals(strategy, professionals, limit=10)

    assert order(items, "technician_id") == [uuid(number) for number in expected]
    assert [item["rank"] for item in items] == [1, 2, 3]
    assert {item["ranking_unit"] for item in items} == {unit}
    assert all(item["reasons"] and isinstance(item["ranking_value"], float) for item in items)


def test_professionals_respect_the_limit_and_do_not_mutate_the_input(professionals):
    snapshot = [dict(item) for item in professionals]

    items = rank_professionals(ProfessionalStrategy.TOP_RATED, professionals, limit=2)

    assert len(items) == 2
    assert professionals == snapshot


def test_professionals_without_candidates_return_nothing():
    assert rank_professionals(ProfessionalStrategy.BEST_MATCH, [], limit=5) == []


def test_professionals_bayesian_rating_pulls_few_reviews_toward_the_platform_mean(professionals):
    items = rank_professionals(ProfessionalStrategy.TOP_RATED, professionals, limit=10)

    perfect_but_new = next(item for item in items if item["technician_id"] == uuid(2))
    assert perfect_but_new["ranking_value"] < 5.0
    assert perfect_but_new["rank"] == 2


@pytest.fixture
def offers():
    return [
        offer(1, power_wp=500.0, efficiency=20.0, unit_price_cents=50000, accepted_proposal_quantity=5),
        offer(
            2,
            power_wp=400.0,
            efficiency=22.0,
            unit_price_cents=32000,
            accepted_proposal_quantity=0,
            supplier_longitude=3.0,
        ),
        offer(
            3,
            power_wp=600.0,
            efficiency=18.0,
            unit_price_cents=90000,
            accepted_proposal_quantity=12,
            supplier_geolocation_count=0,
            supplier_latitude=None,
            supplier_longitude=None,
        ),
    ]


@pytest.mark.parametrize(
    ("strategy", "expected", "unit"),
    [
        (OfferStrategy.BEST_VALUE, [2, 1, 3], "BRL_per_Wp"),
        (OfferStrategy.MOST_EFFICIENT, [2, 1, 3], "percent"),
        (OfferStrategy.MOST_PROVEN, [3, 1, 2], "accepted_proposal_quantity"),
    ],
)
def test_offers_are_ranked_by_each_strategy(offers, strategy, expected, unit):
    items = rank_offers(strategy, None, offers, limit=10)

    assert order(items, "offer_id") == [uuid(200 + number) for number in expected]
    assert {item["ranking_unit"] for item in items} == {unit}
    assert items[0]["unit_price"] == items[0]["unit_price_cents"] / 100


def test_nearest_offers_use_the_unit_location_and_skip_suppliers_without_one(offers):
    items = rank_offers(OfferStrategy.NEAREST_AVAILABLE, LOCAL_UNIT, offers, limit=10)

    assert order(items, "offer_id") == [uuid(201), uuid(202)]
    assert items[0]["distance_km"] == pytest.approx(111.195, abs=0.01)
    assert items[0]["ranking_unit"] == "km"


@pytest.mark.parametrize(
    ("context", "code"),
    [
        (None, "LOCAL_UNIT_REQUIRED"),
        ({**LOCAL_UNIT, "geolocation_count": 0}, "LOCAL_UNIT_GEO_REQUIRED"),
        ({**LOCAL_UNIT, "geolocation_count": 2}, "LOCAL_UNIT_GEO_AMBIGUOUS"),
    ],
)
def test_nearest_offers_require_a_single_located_unit(offers, context, code):
    with pytest.raises(FeedDataUnavailableError) as error:
        rank_offers(OfferStrategy.NEAREST_AVAILABLE, context, offers, limit=10)

    assert error.value.code == code


@pytest.fixture
def suppliers():
    return [
        supplier(1, offer_count=3, accepted_proposal_quantity=5),
        supplier(2, offer_count=5, accepted_proposal_quantity=1, supplier_longitude=3.0),
        supplier(3, offer_count=1, accepted_proposal_quantity=9, supplier_geolocation_count=0),
    ]


@pytest.mark.parametrize(
    ("strategy", "expected", "unit"),
    [
        (SupplierStrategy.MOST_PROVEN, [3, 1, 2], "accepted_proposal_quantity"),
        (SupplierStrategy.BROADEST_CATALOG, [2, 1, 3], "offer_count"),
    ],
)
def test_suppliers_are_ranked_by_each_strategy(suppliers, strategy, expected, unit):
    items = rank_suppliers(strategy, None, suppliers, limit=10)

    assert order(items, "supplier_id") == [uuid(300 + number) for number in expected]
    assert {item["ranking_unit"] for item in items} == {unit}


def test_nearest_suppliers_skip_those_without_a_location(suppliers):
    items = rank_suppliers(SupplierStrategy.NEAREST, LOCAL_UNIT, suppliers, limit=10)

    assert order(items, "supplier_id") == [uuid(301), uuid(302)]
    assert items[0]["distance_km"] < items[1]["distance_km"]


@pytest.mark.parametrize(
    ("context", "code"),
    [
        (None, "LOCAL_UNIT_REQUIRED"),
        ({**LOCAL_UNIT, "geolocation_count": 0}, "LOCAL_UNIT_GEO_REQUIRED"),
        ({**LOCAL_UNIT, "geolocation_count": 3}, "LOCAL_UNIT_GEO_AMBIGUOUS"),
    ],
)
def test_nearest_suppliers_require_a_single_located_unit(suppliers, context, code):
    with pytest.raises(FeedDataUnavailableError) as error:
        rank_suppliers(SupplierStrategy.NEAREST, context, suppliers, limit=10)

    assert error.value.code == code
