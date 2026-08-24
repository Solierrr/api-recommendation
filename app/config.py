from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    API_KEY: str

    class Config:
        env_file = ".env"


settings = Settings()