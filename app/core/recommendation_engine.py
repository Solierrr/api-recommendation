from __future__ import annotations

from datetime import datetime
from math import asin, cos, isfinite, radians, sin, sqrt
from zoneinfo import ZoneInfo

from app.core.errors import RecommendationDataUnavailableError
from app.schemas.recommendations import (
    PanelStrategy,
    ProfessionalStrategy,
    TechnicianStrategy,
)


class RecommendationEngine:
    BAYESIAN_PRIOR_REVIEWS = 5

    @staticmethod
    def _haversine_km(
        origin_latitude: float,
        origin_longitude: float,
        target_latitude: float,
        target_longitude: float,
    ) -> float:
        earth_radius_km = 6371.0088
        latitude_delta = radians(target_latitude - origin_latitude)
        longitude_delta = radians(target_longitude - origin_longitude)
        origin_latitude_radians = radians(origin_latitude)
        target_latitude_radians = radians(target_latitude)
        haversine = sin(latitude_delta / 2) ** 2 + (
            cos(origin_latitude_radians) * cos(target_latitude_radians) * sin(longitude_delta / 2) ** 2
        )
        return 2 * earth_radius_km * asin(sqrt(haversine))

    @staticmethod
    def _normalized(value: float, maximum: float) -> float:
        if maximum <= 0:
            return 0.0
        return max(0.0, min(value / maximum, 1.0))

    @staticmethod
    def _valid_panel_candidate(candidate: dict) -> bool:
        try:
            power_wp = float(candidate["power_wp"])
            efficiency = float(candidate["efficiency"])
            dimension = float(candidate["dimension"])
            weight = float(candidate["weight"])
            unit_price_cents = int(candidate["unit_price_cents"])
            effective_availability = int(candidate["effective_availability"])
        except (KeyError, TypeError, ValueError, OverflowError):
            return False
        return (
            isfinite(power_wp)
            and power_wp > 0
            and isfinite(efficiency)
            and 0 <= efficiency <= 100
            and isfinite(dimension)
            and dimension > 0
            and isfinite(weight)
            and weight > 0
            and unit_price_cents > 0
            and effective_availability > 0
        )

    @classmethod
    def rank_panels(
        cls,
        strategy: PanelStrategy,
        context: dict,
        candidates: list[dict],
        limit: int,
    ) -> tuple[list[dict], list[str]]:
        if strategy is PanelStrategy.TARGET_POWER:
            raise RecommendationDataUnavailableError(
                "TARGET_POWER_DATA_REQUIRED",
                "A unidade não possui dados estruturados suficientes "
                "para calcular a potência-alvo com segurança.",
            )

        warnings: list[str] = []
        ranked = [candidate.copy() for candidate in candidates if cls._valid_panel_candidate(candidate)]

        for candidate in ranked:
            candidate["unit_price"] = candidate["unit_price_cents"] / 100.0
            candidate["price_per_wp"] = candidate["unit_price"] / candidate["power_wp"]
            candidate["distance_km"] = None

        if strategy is PanelStrategy.BEST_VALUE:
            ranked.sort(
                key=lambda item: (
                    item["price_per_wp"],
                    -item["efficiency"],
                    -item["effective_availability"],
                    item["offer_id"],
                )
            )
            ranking_unit = "BRL_per_Wp"
        elif strategy is PanelStrategy.MOST_EFFICIENT:
            ranked.sort(
                key=lambda item: (
                    -item["efficiency"],
                    -item["power_wp"],
                    item["unit_price_cents"],
                    item["offer_id"],
                )
            )
            ranking_unit = "percent"
        elif strategy is PanelStrategy.NEAREST_AVAILABLE:
            if context["geolocation_count"] == 0:
                raise RecommendationDataUnavailableError(
                    "LOCAL_UNIT_GEO_REQUIRED",
                    "A unidade precisa de uma geolocalização para calcular distância.",
                )
            if context["geolocation_count"] > 1:
                raise RecommendationDataUnavailableError(
                    "LOCAL_UNIT_GEO_AMBIGUOUS",
                    "A unidade possui mais de uma geolocalização; "
                    "regularize o cadastro antes de calcular distância.",
                )

            geolocated: list[dict] = []
            for candidate in ranked:
                if candidate["supplier_geolocation_count"] != 1:
                    continue
                candidate["distance_km"] = cls._haversine_km(
                    context["latitude"],
                    context["longitude"],
                    candidate["supplier_latitude"],
                    candidate["supplier_longitude"],
                )
                geolocated.append(candidate)
            ranked = geolocated
            ranked.sort(
                key=lambda item: (
                    item["distance_km"],
                    item["unit_price_cents"],
                    item["offer_id"],
                )
            )
            ranking_unit = "km"
        else:
            ranked.sort(
                key=lambda item: (
                    -item["accepted_proposal_quantity"],
                    item["price_per_wp"],
                    item["offer_id"],
                )
            )
            ranking_unit = "accepted_proposal_quantity"

        def ranking_value(item: dict) -> float:
            if strategy is PanelStrategy.BEST_VALUE:
                return item["price_per_wp"]
            if strategy is PanelStrategy.MOST_EFFICIENT:
                return item["efficiency"]
            if strategy is PanelStrategy.NEAREST_AVAILABLE:
                return item["distance_km"]
            return float(item["accepted_proposal_quantity"])

        def reason(item: dict) -> str:
            if strategy is PanelStrategy.BEST_VALUE:
                return (
                    f"Preço efetivo de R$ {item['price_per_wp']:.2f} por Wp, "
                    f"com eficiência de {item['efficiency']:.2f}%"
                )
            if strategy is PanelStrategy.MOST_EFFICIENT:
                return (
                    f"Eficiência declarada de {item['efficiency']:.2f}% "
                    f"e potência de {item['power_wp']:.2f} Wp"
                )
            if strategy is PanelStrategy.NEAREST_AVAILABLE:
                return f"Oferta com estoque a {item['distance_km']:.2f} km da unidade"
            return (
                f"Modelo presente em {item['accepted_proposal_quantity']} unidade(s) "
                "de propostas aceitas; isso mede adoção comercial, "
                "não desempenho em campo"
            )

        items: list[dict] = []
        for rank, candidate in enumerate(ranked[:limit], start=1):
            items.append(
                {
                    "rank": rank,
                    "model_id": candidate["model_id"],
                    "offer_id": candidate["offer_id"],
                    "supplier_id": candidate["supplier_id"],
                    "brand": candidate["brand"],
                    "model": candidate["model"],
                    "power_wp": candidate["power_wp"],
                    "efficiency": candidate["efficiency"],
                    "dimension": candidate["dimension"],
                    "weight": candidate["weight"],
                    "unit_price": candidate["unit_price"],
                    "effective_availability": candidate["effective_availability"],
                    "accepted_proposal_quantity": candidate["accepted_proposal_quantity"],
                    "distance_km": (
                        round(candidate["distance_km"], 3) if candidate["distance_km"] is not None else None
                    ),
                    "ranking_value": round(float(ranking_value(candidate)), 4),
                    "ranking_unit": ranking_unit,
                    "reasons": [reason(candidate)],
                }
            )
        return items, warnings

    @classmethod
    def _professional_metrics(cls, candidates: list[dict]) -> list[dict]:
        total_reviews = sum(item["review_count_global"] for item in candidates)
        weighted_ratings = sum(
            item["average_rating_global"] * item["review_count_global"] for item in candidates
        )
        platform_mean = weighted_ratings / total_reviews if total_reviews else 0.0

        enriched: list[dict] = []
        for candidate in candidates:
            item = candidate.copy()
            review_count = item["review_count_global"]
            item["adjusted_rating"] = (
                item["average_rating_global"] * review_count + platform_mean * cls.BAYESIAN_PRIOR_REVIEWS
            ) / (review_count + cls.BAYESIAN_PRIOR_REVIEWS)
            resolved_services = item["completed_service_count_global"] + item["canceled_service_count_global"]
            item["resolved_service_count"] = resolved_services
            item["completion_rate"] = (
                item["completed_service_count_global"] / resolved_services if resolved_services else 0.0
            )
            item["reliability_score"] = 0.6 * item["completion_rate"] + 0.4 * (item["adjusted_rating"] / 5.0)
            enriched.append(item)
        return enriched

    @classmethod
    def rank_professionals(
        cls,
        strategy: ProfessionalStrategy,
        candidates: list[dict],
        limit: int,
    ) -> list[dict]:
        ranked = cls._professional_metrics(candidates)

        if strategy is ProfessionalStrategy.TOP_RATED:
            ranked.sort(
                key=lambda item: (
                    -item["adjusted_rating"],
                    -item["review_count_global"],
                    item["name"].casefold(),
                    item["technician_id"],
                )
            )
            unit = "bayesian_rating_0_5"
        elif strategy is ProfessionalStrategy.MOST_QUALIFIED:
            ranked.sort(
                key=lambda item: (
                    -item["valid_certification_count"],
                    -item["adjusted_rating"],
                    item["name"].casefold(),
                    item["technician_id"],
                )
            )
            unit = "valid_certification_count"
        elif strategy is ProfessionalStrategy.MOST_EXPERIENCED:
            ranked.sort(
                key=lambda item: (
                    -item["completed_service_count_global"],
                    -item["adjusted_rating"],
                    item["name"].casefold(),
                    item["technician_id"],
                )
            )
            unit = "completed_service_count_global"
        elif strategy is ProfessionalStrategy.MOST_RELIABLE:
            ranked.sort(
                key=lambda item: (
                    -item["reliability_score"],
                    -item["resolved_service_count"],
                    item["name"].casefold(),
                    item["technician_id"],
                )
            )
            unit = "reliability_score_0_1"
        else:
            max_certifications = max((item["valid_certification_count"] for item in ranked), default=0)
            max_experience = max(
                (item["completed_service_count_global"] for item in ranked),
                default=0,
            )
            for item in ranked:
                item["best_match_score"] = (
                    0.4 * (item["adjusted_rating"] / 5.0)
                    + 0.25 * cls._normalized(item["valid_certification_count"], max_certifications)
                    + 0.2 * cls._normalized(item["completed_service_count_global"], max_experience)
                    + 0.15 * item["reliability_score"]
                )
            ranked.sort(
                key=lambda item: (
                    -item["best_match_score"],
                    -item["review_count_global"],
                    item["name"].casefold(),
                    item["technician_id"],
                )
            )
            unit = "best_match_score_0_1"

        def metric(item: dict) -> float:
            if strategy is ProfessionalStrategy.TOP_RATED:
                return item["adjusted_rating"]
            if strategy is ProfessionalStrategy.MOST_QUALIFIED:
                return float(item["valid_certification_count"])
            if strategy is ProfessionalStrategy.MOST_EXPERIENCED:
                return float(item["completed_service_count_global"])
            if strategy is ProfessionalStrategy.MOST_RELIABLE:
                return item["reliability_score"]
            return item["best_match_score"]

        def reason(item: dict) -> str:
            if strategy is ProfessionalStrategy.TOP_RATED:
                return (
                    f"Avaliação ajustada de {item['adjusted_rating']:.2f}/5, "
                    f"baseada em {item['review_count_global']} avaliação(ões) globais"
                )
            if strategy is ProfessionalStrategy.MOST_QUALIFIED:
                return (
                    f"{item['valid_certification_count']} certificação(ões) "
                    "válida(s) vinculada(s) à profissão"
                )
            if strategy is ProfessionalStrategy.MOST_EXPERIENCED:
                return f"{item['completed_service_count_global']} serviço(s) concluído(s) no histórico global"
            if strategy is ProfessionalStrategy.MOST_RELIABLE:
                return (
                    "Taxa global de conclusão de "
                    f"{item['completion_rate'] * 100:.1f}% em "
                    f"{item['resolved_service_count']} serviço(s) "
                    "concluído(s) ou cancelado(s)"
                )
            return (
                "Combinação de avaliação global, certificações da profissão, "
                "experiência global e taxa de conclusão"
            )

        items: list[dict] = []
        for rank, candidate in enumerate(ranked[:limit], start=1):
            items.append(
                {
                    "rank": rank,
                    "technician_id": candidate["technician_id"],
                    "name": candidate["name"],
                    "profession_id": candidate["profession_id"],
                    "average_rating_global": candidate["average_rating_global"],
                    "review_count_global": candidate["review_count_global"],
                    "completed_service_count_global": candidate["completed_service_count_global"],
                    "assigned_service_count_global": candidate["assigned_service_count_global"],
                    "canceled_service_count_global": candidate["canceled_service_count_global"],
                    "valid_certification_count": candidate["valid_certification_count"],
                    "certification_names": candidate["certification_names"],
                    "ranking_value": round(float(metric(candidate)), 4),
                    "ranking_unit": unit,
                    "reasons": [reason(candidate)],
                }
            )
        return items

    @staticmethod
    def _is_declared_available(shifts: list[dict], scheduled_at: datetime | None, timezone_name: str) -> bool:
        if scheduled_at is None:
            return False
        timezone = ZoneInfo(timezone_name)
        if scheduled_at.tzinfo is None:
            local_schedule = scheduled_at
        else:
            local_schedule = scheduled_at.astimezone(timezone).replace(tzinfo=None)
        return any(
            shift["start_at"] <= local_schedule < shift["end_at"]
            for shift in shifts
            if shift.get("start_at") is not None and shift.get("end_at") is not None
        )

    @classmethod
    def rank_technicians(
        cls,
        strategy: TechnicianStrategy,
        context: dict,
        candidates: list[dict],
        limit: int,
        timezone_name: str,
    ) -> tuple[list[dict], list[str]]:
        ranked = [candidate.copy() for candidate in candidates]
        warnings = [
            "A elegibilidade usa histórico com purpose textual idêntico; "
            "o serviço técnico ainda não declara uma profissão requerida."
        ]

        for candidate in ranked:
            candidate["declared_available_at_schedule"] = cls._is_declared_available(
                candidate["shifts"], context["scheduled_at"], timezone_name
            )
            candidate["affiliation_distance_km"] = None
            if context["geolocation_count"] == 1 and candidate["company_geolocation_count"] == 1:
                candidate["affiliation_distance_km"] = cls._haversine_km(
                    context["latitude"],
                    context["longitude"],
                    candidate["company_latitude"],
                    candidate["company_longitude"],
                )

        if strategy in {TechnicianStrategy.NEAREST, TechnicianStrategy.BEST_ASSIGNMENT}:
            if context["geolocation_count"] == 0:
                raise RecommendationDataUnavailableError(
                    "SERVICE_LOCATION_REQUIRED",
                    "O serviço precisa estar ligado a uma unidade geolocalizada.",
                )
            if context["geolocation_count"] > 1:
                raise RecommendationDataUnavailableError(
                    "SERVICE_LOCATION_AMBIGUOUS",
                    "A unidade do serviço possui mais de uma geolocalização.",
                )
            ranked = [item for item in ranked if item["affiliation_distance_km"] is not None]
            warnings.append(
                "A distância usa o endereço da empresa da afiliação como base "
                "operacional; não representa a localização pessoal do técnico."
            )

        if (
            strategy in {TechnicianStrategy.AVAILABLE, TechnicianStrategy.BEST_ASSIGNMENT}
            and context["scheduled_at"] is None
        ):
            raise RecommendationDataUnavailableError(
                "SERVICE_SCHEDULE_REQUIRED",
                "O serviço precisa de scheduled_date para avaliar disponibilidade.",
            )

        if strategy is TechnicianStrategy.NEAREST:
            ranked.sort(
                key=lambda item: (
                    item["affiliation_distance_km"],
                    -item["same_purpose_completed_count"],
                    item["technician_affiliation_id"],
                )
            )
            unit = "km_from_affiliated_company"
        elif strategy is TechnicianStrategy.AVAILABLE:
            ranked = [item for item in ranked if item["declared_available_at_schedule"]]
            ranked.sort(
                key=lambda item: (
                    -item["same_purpose_completed_count"],
                    -item["average_rating_global"],
                    item["technician_affiliation_id"],
                )
            )
            unit = "declared_available"
        elif strategy is TechnicianStrategy.LEAST_LOADED:
            ranked.sort(
                key=lambda item: (
                    item["active_workload"],
                    -item["same_purpose_completed_count"],
                    -item["average_rating_global"],
                    item["technician_affiliation_id"],
                )
            )
            unit = "active_service_count"
        elif strategy is TechnicianStrategy.MOST_EXPERIENCED:
            ranked.sort(
                key=lambda item: (
                    -item["same_purpose_completed_count"],
                    -item["average_rating_global"],
                    item["active_workload"],
                    item["technician_affiliation_id"],
                )
            )
            unit = "completed_services_with_same_purpose"
        else:
            max_experience = max((item["same_purpose_completed_count"] for item in ranked), default=0)
            max_distance = max((item["affiliation_distance_km"] for item in ranked), default=0.0)
            max_workload = max((item["active_workload"] for item in ranked), default=0)
            for item in ranked:
                distance_score = (
                    1.0 if max_distance <= 0 else 1.0 - item["affiliation_distance_km"] / max_distance
                )
                workload_score = 1.0 if max_workload <= 0 else 1.0 - item["active_workload"] / max_workload
                item["best_assignment_score"] = (
                    0.25 * cls._normalized(item["same_purpose_completed_count"], max_experience)
                    + 0.2 * (item["average_rating_global"] / 5.0)
                    + 0.2 * float(item["declared_available_at_schedule"])
                    + 0.2 * distance_score
                    + 0.15 * workload_score
                )
            ranked.sort(
                key=lambda item: (
                    -item["best_assignment_score"],
                    -item["same_purpose_completed_count"],
                    item["technician_affiliation_id"],
                )
            )
            unit = "best_assignment_score_0_1"

        def metric(item: dict) -> float:
            if strategy is TechnicianStrategy.NEAREST:
                return item["affiliation_distance_km"]
            if strategy is TechnicianStrategy.AVAILABLE:
                return 1.0
            if strategy is TechnicianStrategy.LEAST_LOADED:
                return float(item["active_workload"])
            if strategy is TechnicianStrategy.MOST_EXPERIENCED:
                return float(item["same_purpose_completed_count"])
            return item["best_assignment_score"]

        def reason(item: dict) -> str:
            if strategy is TechnicianStrategy.NEAREST:
                return f"Empresa da afiliação a {item['affiliation_distance_km']:.2f} km da unidade"
            if strategy is TechnicianStrategy.AVAILABLE:
                return (
                    "O horário agendado está contido em um turno declarado; "
                    "conflitos de agenda e deslocamento não são modelados"
                )
            if strategy is TechnicianStrategy.LEAST_LOADED:
                return f"{item['active_workload']} serviço(s) OPEN/IN_PROGRESS atualmente atribuído(s)"
            if strategy is TechnicianStrategy.MOST_EXPERIENCED:
                return (
                    "Executou "
                    f"{item['same_purpose_completed_count']} serviço(s) concluído(s) "
                    "com purpose idêntico"
                )
            return (
                "Combinação de experiência no mesmo purpose, avaliação global, "
                "turno declarado, distância da afiliação e carga ativa"
            )

        items: list[dict] = []
        for rank, candidate in enumerate(ranked[:limit], start=1):
            items.append(
                {
                    "rank": rank,
                    "technician_id": candidate["technician_id"],
                    "technician_affiliation_id": candidate["technician_affiliation_id"],
                    "name": candidate["name"],
                    "target_service_id": context["id"],
                    "affiliation_type": candidate["affiliation_type"],
                    "same_purpose_completed_count": candidate["same_purpose_completed_count"],
                    "average_rating_global": candidate["average_rating_global"],
                    "review_count_global": candidate["review_count_global"],
                    "active_workload": candidate["active_workload"],
                    "declared_available_at_schedule": candidate["declared_available_at_schedule"],
                    "affiliation_distance_km": (
                        round(candidate["affiliation_distance_km"], 3)
                        if candidate["affiliation_distance_km"] is not None
                        else None
                    ),
                    "ranking_value": round(float(metric(candidate)), 4),
                    "ranking_unit": unit,
                    "reasons": [reason(candidate)],
                }
            )
        return items, warnings
