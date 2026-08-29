from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENVIRONMENT: Literal["development", "test", "production"] = "development"
    APP_TIMEZONE: str = "America/Sao_Paulo"
    DOCS_ENABLED: bool = True

    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: SecretStr
    NEO4J_DATABASE: str | None = None

    DB_URL: str = "jdbc:postgresql://localhost:5432/dbsolier"
    DB_USERNAME: str = "solier"
    DB_PASSWORD: SecretStr = SecretStr("solier")
    DB_SSLMODE: str = "disable"

    SYNC_API_KEY: SecretStr | None = None
    RECOMMENDATION_API_KEY: SecretStr | None = None
    SYNC_ON_STARTUP: bool = False
    SYNC_BATCH_SIZE: int = Field(default=500, ge=1, le=5000)
    SYNC_LOCK_LEASE_SECONDS: int = Field(default=900, ge=60, le=3600)
    SYNC_MIN_DOMAIN_RETENTION_RATIO: float = Field(default=0.5, ge=0, le=1)
    SNAPSHOT_MAX_AGE_SECONDS: int = Field(default=86400, ge=60, le=604800)

    RECOMMENDATION_RESULT_LIMIT: int = Field(default=10, ge=1, le=50)
    RECOMMENDATION_POOL_LIMIT: int = Field(default=500, ge=10, le=5000)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("APP_TIMEZONE")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("APP_TIMEZONE deve ser um timezone IANA válido") from error
        return value

    @field_validator("DB_SSLMODE")
    @classmethod
    def validate_sslmode(cls, value: str) -> str:
        normalized = value.lower()
        allowed = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}
        if normalized not in allowed:
            raise ValueError(f"DB_SSLMODE inválido: {value}")
        return normalized

    @property
    def postgres_dsn(self) -> str:
        """Converte a URL JDBC do api-core para uma DSN aceita pelo asyncpg."""
        dsn = self.DB_URL.removeprefix("jdbc:")
        if not dsn.startswith(("postgresql://", "postgres://")):
            raise ValueError("DB_URL deve apontar para PostgreSQL")
        return dsn

    def validate_runtime_security(self) -> None:
        if self.APP_ENVIRONMENT != "production":
            return
        if self.DB_SSLMODE in {"disable", "allow", "prefer"}:
            raise RuntimeError(
                "DB_SSLMODE=require ou superior é obrigatório em produção"
            )
        if not self.NEO4J_URI.lower().startswith(("neo4j+s://", "bolt+s://")):
            raise RuntimeError(
                "NEO4J_URI deve usar neo4j+s:// ou bolt+s:// em produção"
            )
        if self.DOCS_ENABLED:
            raise RuntimeError("DOCS_ENABLED deve ser false em produção")
        sync_api_key = self.SYNC_API_KEY.get_secret_value() if self.SYNC_API_KEY else ""
        if len(sync_api_key) < 32:
            raise RuntimeError(
                "SYNC_API_KEY com pelo menos 32 caracteres é obrigatória em produção"
            )
        recommendation_api_key = (
            self.RECOMMENDATION_API_KEY.get_secret_value()
            if self.RECOMMENDATION_API_KEY
            else ""
        )
        if len(recommendation_api_key) < 32:
            raise RuntimeError(
                "RECOMMENDATION_API_KEY com pelo menos 32 caracteres é "
                "obrigatória em produção"
            )
        if sync_api_key == recommendation_api_key:
            raise RuntimeError(
                "SYNC_API_KEY e RECOMMENDATION_API_KEY devem ser diferentes em produção"
            )


@lru_cache
def get_settings() -> Settings:
    # BaseSettings preenche os campos obrigatórios a partir do ambiente em runtime.
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
