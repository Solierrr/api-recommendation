from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    API_KEY: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()