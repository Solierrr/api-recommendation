from tests.fakes import FakeResult

VERSION = "11111111-1111-4111-8111-111111111111"
UNIT_ID = "22222222-2222-4222-8222-222222222222"
PROFESSION_ID = "33333333-3333-4333-8333-333333333333"
COMPANY_ID = "44444444-4444-4444-8444-444444444444"


def uuid(number: int) -> str:
    return f"00000000-0000-4000-8000-{number:012d}"


def professional(number: int, **overrides) -> dict:
    row = {
        "technician_id": uuid(number),
        "name": f"Profissional {number}",
        "professions": ["Engenheiro Eletricista"],
        "average_rating_global": 4.0,
        "review_count_global": 5,
        "completed_service_count_global": 5,
        "assigned_service_count_global": 6,
        "canceled_service_count_global": 1,
        "valid_certification_count": 1,
        "certification_names": ["NR-10"],
    }
    return {**row, **overrides}


def offer(number: int, **overrides) -> dict:
    row = {
        "model_id": uuid(100 + number),
        "offer_id": uuid(200 + number),
        "supplier_id": uuid(300 + number),
        "supplier_trade_name": f"Fornecedor {number}",
        "brand": "Canadian",
        "model": f"CS{number}",
        "power_wp": 500.0,
        "efficiency": 20.0,
        "dimension": 2.5,
        "weight": 28.0,
        "unit_price_cents": 50000,
        "effective_availability": 10,
        "accepted_proposal_quantity": 0,
        "supplier_geolocation_count": 1,
        "supplier_latitude": 0.0,
        "supplier_longitude": 1.0,
    }
    return {**row, **overrides}


def supplier(number: int, **overrides) -> dict:
    row = {
        "supplier_id": uuid(300 + number),
        "company_id": uuid(400 + number),
        "trade_name": f"Fornecedor {number}",
        "business_type": "DISTRIBUTOR",
        "offer_count": 3,
        "accepted_proposal_quantity": 0,
        "supplier_geolocation_count": 1,
        "supplier_latitude": 0.0,
        "supplier_longitude": 1.0,
    }
    return {**row, **overrides}


LOCAL_UNIT = {"id": UNIT_ID, "geolocation_count": 1, "latitude": 0.0, "longitude": 0.0}


def graph_handler(
    candidates: list[dict], local_unit: dict | None = LOCAL_UNIT, profession: dict | None = None
):
    def handle(query: str, parameters: dict) -> FakeResult:
        if "SyncState" in query:
            return FakeResult(single_return={"active_version": VERSION, "snapshot_age_seconds": 60})
        if "LocalUnit" in query:
            return FakeResult(single_return=local_unit)
        if "RETURN profession.id AS id" in query:
            return FakeResult(single_return=profession or {"id": PROFESSION_ID, "name": "Engenheiro"})
        if "fetch_limit" in query:
            return FakeResult(data_return=candidates)
        raise AssertionError(f"consulta inesperada: {query[:60]}")

    return handle


def fallback_professional(number: int) -> dict:
    row = professional(number)
    return row


def fallback_offer(number: int) -> dict:
    row = offer(number)
    row.pop("supplier_geolocation_count")
    row.pop("supplier_latitude")
    row.pop("supplier_longitude")
    row["price_per_wp"] = row["unit_price_cents"] / 100.0 / row["power_wp"]
    return row


def fallback_supplier(number: int) -> dict:
    row = supplier(number)
    row.pop("supplier_geolocation_count")
    row.pop("supplier_latitude")
    row.pop("supplier_longitude")
    return row
