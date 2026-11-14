"""FastAPI dependency injection providers."""

from functools import lru_cache
from src.api.config import Settings, get_settings


def get_app_settings() -> Settings:
    """Dependency to retrieve application settings."""
    return get_settings()
