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
    # Safety fallback in get_llm(); all agents pass explicit temperatures
    default_temperature: float = 0.7
    # Env-level fallback; prefer PrototypeConfig per-experiment override
    planning_temperature: float = 0.3

    # LangSmith tracing
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "ai-writer-prototype"

    # Vertex AI (optional — for fine-tuning workflows)
    vertex_api_key: str = ""
    vertex_project_id: str = ""
    vertex_region: str = "us-central1"
    vertex_bucket_name: str = ""
    vertex_tuned_model_endpoint: str = ""
    fine_tuning_mock_mode: bool = True


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
