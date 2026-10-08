from enum import StrEnum

from app.errors import FeedDataUnavailableError
from app.feeds.common import Rule, haversine_km, ranked, require_point


class SupplierStrategy(StrEnum):
    MOST_PROVEN = "most_proven"
    BROADEST_CATALOG = "broadest_catalog"
    NEAREST = "nearest"


_RULES: dict[SupplierStrategy, Rule] = {
    SupplierStrategy.MOST_PROVEN: Rule(
        key=lambda item: (-item["accepted_proposal_quantity"], -item["offer_count"], item["supplier_id"]),
        metric=lambda item: float(item["accepted_proposal_quantity"]),
        unit="accepted_proposal_quantity",
        reason=lambda item: (
            f"{item['accepted_proposal_quantity']} unidade(s) em propostas aceitas; "
            "isso mede adoção comercial, não qualidade do serviço"
        ),
    ),
    SupplierStrategy.BROADEST_CATALOG: Rule(
        key=lambda item: (-item["offer_count"], -item["accepted_proposal_quantity"], item["supplier_id"]),
        metric=lambda item: float(item["offer_count"]),
        unit="offer_count",
        reason=lambda item: f"{item['offer_count']} oferta(s) elegível(is) no catálogo",
    ),
    SupplierStrategy.NEAREST: Rule(
        key=lambda item: (item["distance_km"], -item["offer_count"], item["supplier_id"]),
        metric=lambda item: item["distance_km"],
        unit="km",
        reason=lambda item: f"Fornecedor a {item['distance_km']:.2f} km da unidade",
    ),
}


def _nearest(context: dict | None, candidates: list[dict]) -> list[dict]:
    if context is None:
        raise FeedDataUnavailableError(
            "LOCAL_UNIT_REQUIRED", "A estratégia nearest exige o parâmetro local_unit_id."
        )
    require_point(context, "LOCAL_UNIT_GEO_REQUIRED", "LOCAL_UNIT_GEO_AMBIGUOUS", "A unidade")
    located = []
    for candidate in candidates:
        if candidate["supplier_geolocation_count"] != 1:
            continue
        distance = haversine_km(
            context["latitude"],
            context["longitude"],
            candidate["supplier_latitude"],
            candidate["supplier_longitude"],
        )
        located.append({**candidate, "distance_km": round(distance, 3)})
    return located


def rank_suppliers(
    strategy: SupplierStrategy, context: dict | None, candidates: list[dict], limit: int
) -> list[dict]:
    items = [{**candidate, "distance_km": None} for candidate in candidates]
    if strategy is SupplierStrategy.NEAREST:
        items = _nearest(context, items)
    return ranked(items, _RULES[strategy], limit)
