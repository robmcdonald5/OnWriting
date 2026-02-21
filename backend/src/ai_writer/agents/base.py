"""Shared agent infrastructure for LLM access and rate limiting.

Handles two rate-limit concerns for the Gemini free tier:
1. RPM (requests per minute): Proactive sliding-window throttle.
2. 429 retry: Parses the server's retry_delay and waits that long.
   LangChain's built-in retry uses fixed backoff that ignores the
   server's suggested delay — a known issue. We disable it (max_retries=1)
   and handle retries ourselves via the invoke() wrapper.

Usage in agents:
    from ai_writer.agents.base import get_llm, get_structured_llm, invoke

    llm = get_llm(temperature=0.7)
    result = invoke(llm, [{"role": "user", "content": "Hello"}])

    structured_llm = get_structured_llm(MySchema, temperature=0.3)
    result = invoke(structured_llm, [{"role": "user", "content": "..."}])
"""

import logging
import re
import time
from collections import deque
from threading import Lock
from typing import Any

from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from ai_writer.config import get_settings

logger = logging.getLogger("ai_writer.agents.base")

# --- Rate Limiter ---

_call_timestamps: deque[float] = deque()
_rate_lock = Lock()
_RPM_LIMIT = 9  # Stay 1 under the 10 RPM free-tier limit for safety
_MAX_RETRIES = 3
_daily_call_count = 0


def _wait_for_rate_limit() -> None:
    """Block until making a call would stay within the RPM limit."""
    global _daily_call_count

    with _rate_lock:
        now = time.time()
        while _call_timestamps and _call_timestamps[0] <= now - 60:
            _call_timestamps.popleft()

        if len(_call_timestamps) >= _RPM_LIMIT:
            wait_seconds = 60 - (now - _call_timestamps[0]) + 0.5
            if wait_seconds > 0:
                logger.debug(
                    "At %d RPM cap, waiting %.1fs...", _RPM_LIMIT, wait_seconds
                )
                time.sleep(wait_seconds)

        _call_timestamps.append(time.time())
        _daily_call_count += 1
        logger.debug("API call #%d this session", _daily_call_count)


def _parse_retry_delay(error_message: str) -> float:
    """Extract the server-suggested retry delay from a 429 error."""
    match = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", error_message)
    if match:
        return float(match.group(1)) + 1.0
    return 60.0


# --- Public API ---


def get_llm(
    temperature: float | None = None,
    model: str | None = None,
) -> ChatGoogleGenerativeAI:
    """Create a ChatGoogleGenerativeAI instance.

    Returns a plain LLM — use invoke() to call it with rate limiting.
    max_retries=1 disables the SDK's broken retry (it ignores server
    retry_delay). Our invoke() handles retries properly instead.
    """
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=model or settings.default_model,
        temperature=(
            temperature if temperature is not None else settings.default_temperature
        ),
        google_api_key=settings.google_api_key,
        max_retries=1,
    )


def get_structured_llm(
    schema: type[BaseModel],
    temperature: float | None = None,
    model: str | None = None,
) -> Runnable[Any, Any]:
    """Create an LLM that returns structured output as a Pydantic model.

    Returns a Runnable chain — use invoke() to call it with rate limiting.
    """
    llm = get_llm(temperature=temperature, model=model)
    return llm.with_structured_output(schema, method="json_schema")  # type: ignore[arg-type]


def invoke(runnable: Runnable[Any, Any], input: Any, **kwargs: Any) -> Any:
    """Invoke a Runnable with rate limiting and proper 429 retry.

    This is the single entry point for all LLM calls. It:
    1. Enforces the RPM sliding-window throttle
    2. On 429 errors, parses the server's retry_delay and waits
    3. Retries up to _MAX_RETRIES times
    """
    last_error: Exception | None = None

    for attempt in range(_MAX_RETRIES):
        _wait_for_rate_limit()
        try:
            return runnable.invoke(input, **kwargs)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "ResourceExhausted" in error_str:
                delay = _parse_retry_delay(error_str)
                last_error = e
                if attempt < _MAX_RETRIES - 1:
                    logger.warning(
                        "429 hit. Server says wait %.0fs (attempt %d/%d)...",
                        delay,
                        attempt + 1,
                        _MAX_RETRIES,
                    )
                    time.sleep(delay)
                    continue
            raise

    raise last_error  # type: ignore[misc]
