"""Configuration settings for FieldWise AI."""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment or defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "FieldWise AI - Egypt Edition"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:8501",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8501",
        "*",
    ]

    # External APIs
    NASA_POWER_BASE_URL: str = "https://power.larc.nasa.gov/api/temporal/climatology/point"
    SOILGRIDS_BASE_URL: str = "https://rest.isric.org/soilgrids/v2.0/properties/query"

    # Cache Settings
    CACHE_TTL_DAYS: int = 30
    CACHE_DB_PATH: str = "data/processed/cache.sqlite"

    # Voice Assistant Configuration
    ASR_PROVIDER: str = "browser"
    TTS_PROVIDER: str = "browser"
    LLM_PARSER_PROVIDER: str = "deterministic"
    OPENAI_API_KEY: str | None = None


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
