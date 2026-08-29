from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PanelStrategy(StrEnum):
    BEST_VALUE = "best_value"
    TARGET_POWER = "target_power"
    MOST_EFFICIENT = "most_efficient"
    NEAREST_AVAILABLE = "nearest_available"
    MOST_PROVEN = "most_proven"


class ProfessionalStrategy(StrEnum):
    TOP_RATED = "top_rated"
    MOST_QUALIFIED = "most_qualified"
    MOST_EXPERIENCED = "most_experienced"
    MOST_RELIABLE = "most_reliable"
    BEST_MATCH = "best_match"


class TechnicianStrategy(StrEnum):
    NEAREST = "nearest"
    AVAILABLE = "available"
    LEAST_LOADED = "least_loaded"
    MOST_EXPERIENCED = "most_experienced"
    BEST_ASSIGNMENT = "best_assignment"


class RecommendationContext(BaseModel):
    type: Literal["local_unit", "profession", "technical_service"]
    id: UUID
    strategy: str
    generated_at: datetime
    sync_version: UUID


class PanelRecommendationItem(BaseModel):
    rank: int = Field(ge=1)
    model_id: UUID
    offer_id: UUID
    supplier_id: UUID
    brand: str
    model: str
    power_wp: float = Field(gt=0)
    efficiency: float = Field(ge=0, le=100)
    dimension: float = Field(gt=0)
    weight: float = Field(gt=0)
    unit_price: float = Field(gt=0)
    effective_availability: int = Field(gt=0)
    accepted_proposal_quantity: int = Field(ge=0)
    distance_km: float | None = Field(default=None, ge=0)
    ranking_value: float = Field(ge=0)
    ranking_unit: str
    reasons: list[str]


class ProfessionalRecommendationItem(BaseModel):
    rank: int = Field(ge=1)
    technician_id: UUID
    name: str
    profession_id: UUID
    average_rating_global: float = Field(ge=0, le=5)
    review_count_global: int = Field(ge=0)
    completed_service_count_global: int = Field(ge=0)
    assigned_service_count_global: int = Field(ge=0)
    canceled_service_count_global: int = Field(ge=0)
    valid_certification_count: int = Field(ge=0)
    certification_names: list[str]
    ranking_value: float = Field(ge=0)
    ranking_unit: str
    reasons: list[str]


class TechnicianRecommendationItem(BaseModel):
    rank: int = Field(ge=1)
    technician_id: UUID
    technician_affiliation_id: UUID
    name: str
    target_service_id: UUID
    affiliation_type: str
    same_purpose_completed_count: int = Field(ge=1)
    average_rating_global: float = Field(ge=0, le=5)
    review_count_global: int = Field(ge=0)
    active_workload: int = Field(ge=0)
    declared_available_at_schedule: bool
    affiliation_distance_km: float | None = Field(default=None, ge=0)
    ranking_value: float = Field(ge=0)
    ranking_unit: str
    reasons: list[str]


class PanelRecommendationResponse(BaseModel):
    context: RecommendationContext
    items: list[PanelRecommendationItem]
    warnings: list[str] = Field(default_factory=list)


class ProfessionalRecommendationResponse(BaseModel):
    context: RecommendationContext
    items: list[ProfessionalRecommendationItem]
    warnings: list[str] = Field(default_factory=list)


class TechnicianRecommendationResponse(BaseModel):
    context: RecommendationContext
    items: list[TechnicianRecommendationItem]
    warnings: list[str] = Field(default_factory=list)
