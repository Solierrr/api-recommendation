from uuid import UUID

from pydantic import BaseModel, Field


class PublicProfessional(BaseModel):
    technician_id: UUID
    name: str
    professions: list[str]
    average_rating_global: float = Field(ge=0, le=5)
    review_count_global: int = Field(ge=0)
    completed_service_count_global: int = Field(ge=0)
    certification_names: list[str]


class ProfessionalItem(PublicProfessional):
    rank: int = Field(ge=1)
    assigned_service_count_global: int = Field(ge=0)
    canceled_service_count_global: int = Field(ge=0)
    valid_certification_count: int = Field(ge=0)
    ranking_value: float = Field(ge=0)
    ranking_unit: str
    reasons: list[str]
