from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.errors import RecommendationDataUnavailableError
from app.core.recommendation_engine import RecommendationEngine
from app.schemas.recommendations import (
    PanelStrategy,
    ProfessionalStrategy,
    TechnicianStrategy,
)


def panel_candidate(**overrides):
    candidate = {
        "model_id": str(uuid4()),
        "offer_id": str(uuid4()),
        "supplier_id": str(uuid4()),
        "brand": "Sol",
        "model": "X1",
        "power_wp": 500.0,
        "efficiency": 20.0,
        "dimension": 2.0,
        "weight": 25.0,
        "unit_price_cents": 100_000,
        "effective_availability": 10,
        "accepted_proposal_quantity": 0,
        "supplier_geolocation_count": 1,
        "supplier_latitude": -23.5505,
        "supplier_longitude": -46.6333,
    }
    candidate.update(overrides)
    return candidate


def professional_candidate(**overrides):
    candidate = {
        "technician_id": str(uuid4()),
        "name": "Ana",
        "profession_id": str(uuid4()),
        "average_rating_global": 4.5,
        "review_count_global": 10,
        "completed_service_count_global": 8,
        "assigned_service_count_global": 10,
        "canceled_service_count_global": 1,
        "valid_certification_count": 2,
        "certification_names": ["NR10", "NR35"],
    }
    candidate.update(overrides)
    return candidate


def technician_candidate(schedule: datetime, **overrides):
    candidate = {
        "technician_id": str(uuid4()),
        "technician_affiliation_id": str(uuid4()),
        "name": "Ana",
        "affiliation_type": "AFFILIATED",
        "same_purpose_completed_count": 3,
        "average_rating_global": 4.5,
        "review_count_global": 10,
        "active_workload": 1,
        "company_geolocation_count": 1,
        "company_latitude": -23.5505,
        "company_longitude": -46.6333,
        "shifts": [
            {
                "start_at": schedule.replace(tzinfo=None) - timedelta(hours=1),
                "end_at": schedule.replace(tzinfo=None) + timedelta(hours=1),
            }
        ],
    }
    candidate.update(overrides)
    return candidate


def test_best_value_uses_price_per_watt() -> None:
    expensive = panel_candidate(unit_price_cents=120_000, power_wp=500.0)
    efficient_value = panel_candidate(unit_price_cents=100_000, power_wp=550.0)

    items, warnings = RecommendationEngine.rank_panels(
        PanelStrategy.BEST_VALUE,
        {"geolocation_count": 0, "latitude": None, "longitude": None},
        [expensive, efficient_value],
        limit=10,
    )

    assert items[0]["offer_id"] == efficient_value["offer_id"]
    assert items[0]["ranking_unit"] == "BRL_per_Wp"
    assert warnings == []


def test_nearest_panel_rejects_ambiguous_unit_geolocation() -> None:
    with pytest.raises(RecommendationDataUnavailableError) as error:
        RecommendationEngine.rank_panels(
            PanelStrategy.NEAREST_AVAILABLE,
            {"geolocation_count": 2, "latitude": None, "longitude": None},
            [panel_candidate()],
            limit=10,
        )

    assert error.value.code == "LOCAL_UNIT_GEO_AMBIGUOUS"


def test_target_power_does_not_invent_energy_calculation() -> None:
    with pytest.raises(RecommendationDataUnavailableError) as error:
        RecommendationEngine.rank_panels(
            PanelStrategy.TARGET_POWER,
            {"geolocation_count": 0, "latitude": None, "longitude": None},
            [panel_candidate()],
            limit=10,
        )

    assert error.value.code == "TARGET_POWER_DATA_REQUIRED"


def test_most_qualified_professional_uses_valid_certification_count() -> None:
    less_qualified = professional_candidate(valid_certification_count=1)
    more_qualified = professional_candidate(valid_certification_count=4)

    items = RecommendationEngine.rank_professionals(
        ProfessionalStrategy.MOST_QUALIFIED,
        [less_qualified, more_qualified],
        limit=10,
    )

    assert items[0]["technician_id"] == more_qualified["technician_id"]
    assert items[0]["ranking_value"] == 4


def test_reliability_uses_completion_rate_and_rating() -> None:
    unreliable = professional_candidate(
        completed_service_count_global=2,
        assigned_service_count_global=10,
        average_rating_global=5.0,
    )
    reliable = professional_candidate(
        completed_service_count_global=9,
        assigned_service_count_global=10,
        average_rating_global=4.5,
    )

    items = RecommendationEngine.rank_professionals(
        ProfessionalStrategy.MOST_RELIABLE,
        [unreliable, reliable],
        limit=10,
    )

    assert items[0]["technician_id"] == reliable["technician_id"]


def test_available_technician_requires_schedule() -> None:
    with pytest.raises(RecommendationDataUnavailableError) as error:
        RecommendationEngine.rank_technicians(
            TechnicianStrategy.AVAILABLE,
            {
                "id": str(uuid4()),
                "scheduled_at": None,
                "geolocation_count": 0,
                "latitude": None,
                "longitude": None,
            },
            [],
            limit=10,
            timezone_name="UTC",
        )

    assert error.value.code == "SERVICE_SCHEDULE_REQUIRED"


def test_available_technician_is_filtered_by_declared_shift() -> None:
    schedule = datetime(2026, 4, 10, 14, 0, tzinfo=UTC)
    available = technician_candidate(schedule)
    unavailable = technician_candidate(
        schedule,
        shifts=[
            {
                "start_at": datetime(2026, 4, 10, 8, 0),
                "end_at": datetime(2026, 4, 10, 10, 0),
            }
        ],
    )

    items, warnings = RecommendationEngine.rank_technicians(
        TechnicianStrategy.AVAILABLE,
        {
            "id": str(uuid4()),
            "scheduled_at": schedule,
            "geolocation_count": 0,
            "latitude": None,
            "longitude": None,
        },
        [unavailable, available],
        limit=10,
        timezone_name="UTC",
    )

    assert [item["technician_id"] for item in items] == [available["technician_id"]]
    assert warnings


def test_nearest_technician_uses_affiliated_company_as_explicit_proxy() -> None:
    schedule = datetime(2026, 4, 10, 14, 0, tzinfo=UTC)
    near = technician_candidate(
        schedule,
        company_latitude=-23.551,
        company_longitude=-46.634,
    )
    far = technician_candidate(
        schedule,
        company_latitude=-22.9068,
        company_longitude=-43.1729,
    )

    items, warnings = RecommendationEngine.rank_technicians(
        TechnicianStrategy.NEAREST,
        {
            "id": str(uuid4()),
            "scheduled_at": schedule,
            "geolocation_count": 1,
            "latitude": -23.5505,
            "longitude": -46.6333,
        },
        [far, near],
        limit=10,
        timezone_name="UTC",
    )

    assert items[0]["technician_id"] == near["technician_id"]
    assert any("empresa da afiliação" in warning for warning in warnings)


def test_open_services_do_not_reduce_reliability() -> None:
    many_open_services = professional_candidate(
        completed_service_count_global=8,
        canceled_service_count_global=0,
        assigned_service_count_global=100,
    )
    cancellations = professional_candidate(
        completed_service_count_global=8,
        canceled_service_count_global=2,
        assigned_service_count_global=10,
    )

    items = RecommendationEngine.rank_professionals(
        ProfessionalStrategy.MOST_RELIABLE,
        [cancellations, many_open_services],
        limit=10,
    )

    assert items[0]["technician_id"] == many_open_services["technician_id"]
    assert "concluído(s) ou cancelado(s)" in items[0]["reasons"][0]


def test_invalid_panel_values_are_filtered_before_division() -> None:
    valid = panel_candidate()
    invalid = panel_candidate(power_wp=0)

    items, _ = RecommendationEngine.rank_panels(
        PanelStrategy.BEST_VALUE,
        {"geolocation_count": 0, "latitude": None, "longitude": None},
        [invalid, valid],
        limit=10,
    )

    assert [item["offer_id"] for item in items] == [valid["offer_id"]]
