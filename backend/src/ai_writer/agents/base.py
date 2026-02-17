"""Shared agent infrastructure for LLM access and rate limiting."""

import time
from collections import deque
from threading import Lock
from typing import Any

from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from ai_writer.config import get_settings

# --- Rate Limiter ---

_call_timestamps: deque[float] = deque()
_rate_lock = Lock()
_RPM_LIMIT = 9  # Stay 1 under the 10 RPM free-tier limit for safety


def _wait_for_rate_limit() -> None:
    """Block until making a call would stay within the RPM limit.

    Tracks timestamps of recent calls in a sliding 60-second window.
    If at capacity, sleeps until the oldest call falls outside the window.
    """
    with _rate_lock:
        now = time.time()
        # Discard timestamps older than 60 seconds
        while _call_timestamps and _call_timestamps[0] <= now - 60:
            _call_timestamps.popleft()

        if len(_call_timestamps) >= _RPM_LIMIT:
            wait_seconds = 60 - (now - _call_timestamps[0]) + 0.5
            if wait_seconds > 0:
                print(f"  [Rate Limiter] At {_RPM_LIMIT} RPM cap, waiting {wait_seconds:.1f}s...", flush=True)
                time.sleep(wait_seconds)

        _call_timestamps.append(time.time())


# --- LLM Factories ---


def _build_llm_kwargs(
    temperature: float | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Resolve LLM constructor kwargs from settings and overrides."""
    settings = get_settings()
    return {
        "model": model or settings.default_model,
        "temperature": temperature if temperature is not None else settings.default_temperature,
        "google_api_key": settings.google_api_key,
        "max_retries": 3,
    }


def get_llm(
    temperature: float | None = None,
    model: str | None = None,
) -> ChatGoogleGenerativeAI:
    """Create a rate-limited ChatGoogleGenerativeAI instance."""
    return _RateLimitedLLM(**_build_llm_kwargs(temperature, model))


def get_structured_llm(
    schema: type[BaseModel],
    temperature: float | None = None,
    model: str | None = None,
) -> Runnable[Any, Any]:
    """Create an LLM that returns structured output as a Pydantic model."""
    llm = get_llm(temperature=temperature, model=model)
    return llm.with_structured_output(schema, method="json_schema")  # type: ignore[arg-type]


class _RateLimitedLLM(ChatGoogleGenerativeAI):
    """ChatGoogleGenerativeAI subclass that enforces RPM rate limiting."""

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        _wait_for_rate_limit()
        return super().invoke(*args, **kwargs)

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        _wait_for_rate_limit()
        return await super().ainvoke(*args, **kwargs)
