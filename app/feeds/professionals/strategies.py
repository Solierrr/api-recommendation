from enum import StrEnum

from app.feeds.common import Rule, normalized, ranked

BAYESIAN_PRIOR_REVIEWS = 5


class ProfessionalStrategy(StrEnum):
    TOP_RATED = "top_rated"
    MOST_QUALIFIED = "most_qualified"
    MOST_EXPERIENCED = "most_experienced"
    MOST_RELIABLE = "most_reliable"
    BEST_MATCH = "best_match"


def _tie(item: dict) -> tuple[str, str]:
    return item["name"].casefold(), item["technician_id"]


_RULES: dict[ProfessionalStrategy, Rule] = {
    ProfessionalStrategy.TOP_RATED: Rule(
        key=lambda item: (-item["adjusted_rating"], -item["review_count_global"], *_tie(item)),
        metric=lambda item: item["adjusted_rating"],
        unit="bayesian_rating_0_5",
        reason=lambda item: (
            f"Avaliação ajustada de {item['adjusted_rating']:.2f}/5, "
            f"baseada em {item['review_count_global']} avaliação(ões) globais"
        ),
    ),
    ProfessionalStrategy.MOST_QUALIFIED: Rule(
        key=lambda item: (-item["valid_certification_count"], -item["adjusted_rating"], *_tie(item)),
        metric=lambda item: float(item["valid_certification_count"]),
        unit="valid_certification_count",
        reason=lambda item: f"{item['valid_certification_count']} certificação(ões) válida(s)",
    ),
    ProfessionalStrategy.MOST_EXPERIENCED: Rule(
        key=lambda item: (-item["completed_service_count_global"], -item["adjusted_rating"], *_tie(item)),
        metric=lambda item: float(item["completed_service_count_global"]),
        unit="completed_service_count_global",
        reason=lambda item: (
            f"{item['completed_service_count_global']} serviço(s) concluído(s) no histórico global"
        ),
    ),
    ProfessionalStrategy.MOST_RELIABLE: Rule(
        key=lambda item: (-item["reliability_score"], -item["resolved_service_count"], *_tie(item)),
        metric=lambda item: item["reliability_score"],
        unit="reliability_score_0_1",
        reason=lambda item: (
            f"Taxa global de conclusão de {item['completion_rate'] * 100:.1f}% em "
            f"{item['resolved_service_count']} serviço(s) concluído(s) ou cancelado(s)"
        ),
    ),
    ProfessionalStrategy.BEST_MATCH: Rule(
        key=lambda item: (-item["best_match_score"], -item["review_count_global"], *_tie(item)),
        metric=lambda item: item["best_match_score"],
        unit="best_match_score_0_1",
        reason=lambda item: (
            "Combinação de avaliação global, certificações, experiência global e taxa de conclusão"
        ),
    ),
}


def _enrich(candidates: list[dict]) -> list[dict]:
    total_reviews = sum(item["review_count_global"] for item in candidates)
    weighted_ratings = sum(item["average_rating_global"] * item["review_count_global"] for item in candidates)
    platform_mean = weighted_ratings / total_reviews if total_reviews else 0.0

    enriched = []
    for candidate in candidates:
        reviews = candidate["review_count_global"]
        resolved = candidate["completed_service_count_global"] + candidate["canceled_service_count_global"]
        adjusted = (candidate["average_rating_global"] * reviews + platform_mean * BAYESIAN_PRIOR_REVIEWS) / (
            reviews + BAYESIAN_PRIOR_REVIEWS
        )
        completion_rate = candidate["completed_service_count_global"] / resolved if resolved else 0.0
        enriched.append(
            {
                **candidate,
                "adjusted_rating": adjusted,
                "resolved_service_count": resolved,
                "completion_rate": completion_rate,
                "reliability_score": 0.6 * completion_rate + 0.4 * (adjusted / 5.0),
            }
        )
    return enriched


def _score_best_match(candidates: list[dict]) -> None:
    max_certifications = max((item["valid_certification_count"] for item in candidates), default=0)
    max_experience = max((item["completed_service_count_global"] for item in candidates), default=0)
    for item in candidates:
        item["best_match_score"] = (
            0.4 * (item["adjusted_rating"] / 5.0)
            + 0.25 * normalized(item["valid_certification_count"], max_certifications)
            + 0.2 * normalized(item["completed_service_count_global"], max_experience)
            + 0.15 * item["reliability_score"]
        )


def rank_professionals(strategy: ProfessionalStrategy, candidates: list[dict], limit: int) -> list[dict]:
    enriched = _enrich(candidates)
    if strategy is ProfessionalStrategy.BEST_MATCH:
        _score_best_match(enriched)
    return ranked(enriched, _RULES[strategy], limit)
