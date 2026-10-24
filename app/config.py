import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DOCS_ENABLED: bool = True

    DB_NEO4J_URI: str | None = None
    DB_NEO4J_USER: str = "neo4j"
    DB_NEO4J_PASSWORD: SecretStr | None = None
    DB_NEO4J_FEED: str | None = None
    GRAPH_TIMEOUT_SECONDS: float = Field(default=3.0, gt=0, le=30)
    GRAPH_RETRY_AFTER_SECONDS: int = Field(default=30, ge=0, le=3600)

    RECOMMENDATION_API_KEY: SecretStr | None = None
    RECOMMENDATION_RESULT_LIMIT: int = Field(default=10, ge=1, le=50)
    RECOMMENDATION_POOL_LIMIT: int = Field(default=500, ge=10, le=5000)
    PUBLIC_CACHE_SECONDS: int = Field(default=300, ge=0, le=86400)
    PUBLIC_STALE_IF_ERROR_SECONDS: int = Field(default=86400, ge=0, le=604800)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def graph_configured(self) -> bool:
        return bool(self.DB_NEO4J_URI and self.DB_NEO4J_PASSWORD)

    def validate_runtime_security(self) -> None:
        if self.APP_ENVIRONMENT != "production":
            return
        if self.DOCS_ENABLED:
            raise RuntimeError("DOCS_ENABLED deve ser false em produção")
        if self.RECOMMENDATION_API_KEY is None:
            raise RuntimeError("RECOMMENDATION_API_KEY é obrigatória em produção")
        if not 32 <= len(self.RECOMMENDATION_API_KEY.get_secret_value()) <= 512:
            raise RuntimeError("RECOMMENDATION_API_KEY deve ter entre 32 e 512 caracteres em produção")


@lru_cache
def get_settings() -> Settings:
    env_file = None if os.environ.get("APP_ENVIRONMENT") == "test" else ".env"
    return Settings(_env_file=env_file)  # type: ignore[call-arg]


settings = get_settings()
