from uuid import UUID

from pydantic import BaseModel, Field


class PublicSupplier(BaseModel):
    supplier_id: UUID
    trade_name: str
    business_type: str | None
    offer_count: int = Field(ge=1)


class SupplierItem(PublicSupplier):
    rank: int = Field(ge=1)
    company_id: UUID
    accepted_proposal_quantity: int = Field(ge=0)
    distance_km: float | None = Field(default=None, ge=0)
    ranking_value: float = Field(ge=0)
    ranking_unit: str
    reasons: list[str]
