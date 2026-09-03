from pydantic import BaseModel, Field, model_validator


class RecommendationRequest(BaseModel):
    service_name: str = Field(
        ...,
        min_length=1,
        description="Nome exato do serviço buscado",
        examples=["Desenvolvimento Python"],
    )
    min_rating: float | None = Field(
        default=None,
        ge=0,
        le=5,
        description="Nota média mínima, aplicada estritamente",
    )
    min_level: int = Field(
        default=2,
        ge=1,
        le=5,
        json_schema_extra={"deprecated": True},
        description="Alias legado de min_rating",
    )
    limit: int = Field(default=5, ge=1, le=20, description="Quantidade máxima de recomendações")

    @model_validator(mode="after")
    def validate_rating_alias(self):
        if self.min_rating is not None and "min_level" in self.model_fields_set:
            raise ValueError("Informe somente min_rating ou o alias legado min_level")
        return self

    @property
    def resolved_min_rating(self) -> float:
        if self.min_rating is not None:
            return self.min_rating
        return float(self.min_level)


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
