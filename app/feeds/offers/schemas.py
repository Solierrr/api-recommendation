from uuid import UUID

from pydantic import BaseModel, Field


class PublicOffer(BaseModel):
    offer_id: UUID
    supplier_id: UUID
    supplier_trade_name: str
    brand: str
    model: str
    power_wp: float = Field(gt=0)
    efficiency: float = Field(ge=0, le=100)
    unit_price: float = Field(gt=0)
    effective_availability: int = Field(gt=0)


class OfferItem(PublicOffer):
    rank: int = Field(ge=1)
    model_id: UUID
    dimension: float = Field(gt=0)
    weight: float = Field(gt=0)
    accepted_proposal_quantity: int = Field(ge=0)
    distance_km: float | None = Field(default=None, ge=0)
    ranking_value: float = Field(ge=0)
    ranking_unit: str
    reasons: list[str]
