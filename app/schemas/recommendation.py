from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    service_name: str = Field(
        ...,
        min_length=1,
        description="Nome exato do serviço buscado",
        examples=["Desenvolvimento Python"],
    )
    min_level: int = Field(default=2, ge=1, le=5, description="Nível mínimo de qualificação")
    limit: int = Field(default=5, ge=1, le=20, description="Quantidade máxima de recomendações")


class CandidateResponse(BaseModel):
    candidate_id: str
    name: str
    service: str
    qualifications: list[str]
    avg_qualification_score: float
    score: float
    reasons: list[str]


class RecommendationResponse(BaseModel):
    total: int
    data: list[CandidateResponse]
