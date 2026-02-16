"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google Gemini
    google_api_key: str = ""
    default_model: str = "gemini-2.5-flash"
    default_temperature: float = 0.7
    planning_temperature: float = 0.3

    # LangSmith tracing
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "ai-writer-prototype"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
