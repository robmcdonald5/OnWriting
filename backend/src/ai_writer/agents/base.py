"""Shared agent infrastructure for LLM access."""

from typing import Any

from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from ai_writer.config import get_settings


def get_llm(
    temperature: float | None = None,
    model: str | None = None,
) -> ChatGoogleGenerativeAI:
    """Create a ChatGoogleGenerativeAI instance with project defaults."""
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=model or settings.default_model,
        temperature=(
            temperature if temperature is not None else settings.default_temperature
        ),
        google_api_key=settings.google_api_key,
    )


def get_structured_llm(
    schema: type[BaseModel],
    temperature: float | None = None,
    model: str | None = None,
) -> Runnable[Any, Any]:
    """Create an LLM that returns structured output as a Pydantic model."""
    llm = get_llm(temperature=temperature, model=model)
    return llm.with_structured_output(schema, method="json_schema")  # type: ignore[arg-type]
