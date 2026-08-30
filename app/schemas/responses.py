from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LivenessResponse(BaseModel):
    status: Literal["alive"]


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    postgres: Literal["connected"]
    neo4j: Literal["connected"]
    active_sync_version: UUID
    snapshot_age_seconds: int = Field(ge=0)
    snapshot_node_count: int = Field(gt=0)


class HealthResponse(BaseModel):
    status: Literal["online"]
    postgres: Literal["connected"]
    neo4j: Literal["connected"]


class CandidateResponse(BaseModel):
    candidate_id: UUID
    name: str
    service: str
    qualifications: list[str]
    average_rating: float = Field(ge=0, le=5)
    review_count: int = Field(ge=0)
    score: float = Field(ge=0, le=1)
    reasons: list[str]


class SyncResponse(BaseModel):
    status: Literal["synchronized"]
    sync_version: UUID
    local_units: int = Field(ge=0)
    panel_models: int = Field(ge=0)
    panel_offers: int = Field(ge=0)
    professionals: int = Field(ge=0)
    professions: int = Field(ge=0)
    services: int = Field(ge=0)
    qualifications: int = Field(ge=0)
    technician_affiliations: int = Field(ge=0)
    technical_services: int = Field(ge=0)
