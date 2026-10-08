from enum import StrEnum

from app.errors import FeedDataUnavailableError
from app.feeds.common import Rule, haversine_km, ranked, require_point


class OfferStrategy(StrEnum):
    BEST_VALUE = "best_value"
    MOST_EFFICIENT = "most_efficient"
    NEAREST_AVAILABLE = "nearest_available"
    MOST_PROVEN = "most_proven"


_RULES: dict[OfferStrategy, Rule] = {
    OfferStrategy.BEST_VALUE: Rule(
        key=lambda item: (
            item["price_per_wp"],
            -item["efficiency"],
            -item["effective_availability"],
            item["offer_id"],
        ),
        metric=lambda item: item["price_per_wp"],
        unit="BRL_per_Wp",
        reason=lambda item: (
            f"Preço efetivo de R$ {item['price_per_wp']:.2f} por Wp, com eficiência de {item['efficiency']:.2f}%"
        ),
    ),
    OfferStrategy.MOST_EFFICIENT: Rule(
        key=lambda item: (-item["efficiency"], -item["power_wp"], item["unit_price_cents"], item["offer_id"]),
        metric=lambda item: item["efficiency"],
        unit="percent",
        reason=lambda item: (
            f"Eficiência declarada de {item['efficiency']:.2f}% e potência de {item['power_wp']:.2f} Wp"
        ),
    ),
    OfferStrategy.NEAREST_AVAILABLE: Rule(
        key=lambda item: (item["distance_km"], item["unit_price_cents"], item["offer_id"]),
        metric=lambda item: item["distance_km"],
        unit="km",
        reason=lambda item: f"Oferta com estoque a {item['distance_km']:.2f} km da unidade",
    ),
    OfferStrategy.MOST_PROVEN: Rule(
        key=lambda item: (-item["accepted_proposal_quantity"], item["price_per_wp"], item["offer_id"]),
        metric=lambda item: float(item["accepted_proposal_quantity"]),
        unit="accepted_proposal_quantity",
        reason=lambda item: (
            f"Modelo presente em {item['accepted_proposal_quantity']} unidade(s) de propostas aceitas; "
            "isso mede adoção comercial, não desempenho em campo"
        ),
    ),
}


def with_prices(candidates: list[dict]) -> list[dict]:
    return [
        {
            **candidate,
            "unit_price": candidate["unit_price_cents"] / 100.0,
            "price_per_wp": candidate["unit_price_cents"] / 100.0 / candidate["power_wp"],
            "distance_km": None,
        }
        for candidate in candidates
    ]


def _nearest(context: dict | None, candidates: list[dict]) -> list[dict]:
    if context is None:
        raise FeedDataUnavailableError(
            "LOCAL_UNIT_REQUIRED", "A estratégia nearest_available exige o parâmetro local_unit_id."
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


def rank_offers(
    strategy: OfferStrategy, context: dict | None, candidates: list[dict], limit: int
) -> list[dict]:
    items = with_prices(candidates)
    if strategy is OfferStrategy.NEAREST_AVAILABLE:
        items = _nearest(context, items)
    return ranked(items, _RULES[strategy], limit)
