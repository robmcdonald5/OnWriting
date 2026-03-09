"""LLM factories with mock mode support.

Provides:
- get_vertex_llm() — Vertex AI for fine-tuned model inference
- get_openrouter_llm() — OpenRouter for cross-family judge models
- get_openrouter_structured_llm() — OpenRouter with structured output

Mocks implement LangChain's Runnable interface so the entire comparison
pipeline runs end-to-end without credentials.
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable, RunnableConfig
from pydantic import BaseModel

from ai_writer.config import get_settings

logger = logging.getLogger("ai_writer.fine_tuning.llm")

_MOCK_CREATIVE_TEXT = """\
The corridor stretched ahead, narrow and low-ceilinged, \
smelling of wet plaster and the faint chemical sweetness \
of something recently cleaned. Fluorescent tubes buzzed \
overhead, every third one dark. Her footsteps echoed back \
at her from tile that had once been white and was now the \
colour of old teeth.

She stopped at the second door on the left. The number \
had been painted over but she could still read it through \
the latex: 714. She pressed her ear to the wood and listened. \
Nothing. Or almost nothing — a sound like breathing, if \
breathing could be mechanical, rhythmic as a pump.

She tried the handle. It turned.\
"""


class _MockTunedLLM(Runnable[Any, AIMessage]):
    """Mock tuned LLM that returns synthetic creative text.

    Implements Runnable.invoke() to satisfy the LangChain interface.
    Returns an AIMessage with placeholder prose.
    """

    def __init__(self, model_name: str = "mock-tuned-model"):
        super().__init__()
        self.model_name = model_name

    def invoke(  # noqa: A002
        self, input: Any, config: RunnableConfig | None = None, **kwargs: Any
    ) -> AIMessage:
        logger.info("[MOCK] Tuned model '%s' invoked", self.model_name)
        return AIMessage(content=_MOCK_CREATIVE_TEXT)

    async def ainvoke(  # noqa: A002
        self, input: Any, config: RunnableConfig | None = None, **kwargs: Any
    ) -> AIMessage:
        return self.invoke(input, config, **kwargs)


def get_vertex_llm(
    model_endpoint: str = "",
    temperature: float = 0.7,
    mock_mode: bool | None = None,
) -> Runnable:
    """Get a Vertex AI LLM for fine-tuned model inference.

    Args:
        model_endpoint: Vertex AI endpoint resource name or ID.
            If empty, uses settings.vertex_tuned_model_endpoint.
        temperature: Sampling temperature.
        mock_mode: Override mock mode. None = use settings.fine_tuning_mock_mode.

    Returns:
        A Runnable that returns AIMessage.
    """
    settings = get_settings()
    use_mock = mock_mode if mock_mode is not None else settings.fine_tuning_mock_mode

    if use_mock:
        logger.info("Using mock tuned LLM (mock_mode=True)")
        return _MockTunedLLM(model_name="mock-tuned-model")

    endpoint = model_endpoint or settings.vertex_tuned_model_endpoint
    if not endpoint:
        raise ValueError("vertex_tuned_model_endpoint must be set when mock_mode=False")

    try:
        from langchain_google_vertexai import ChatVertexAI  # type: ignore[import-not-found]  # noqa: I001
    except ImportError as exc:
        raise ImportError(
            "langchain-google-vertexai is required for real Vertex AI inference. "
            "Install with: poetry install --with fine-tuning"
        ) from exc

    logger.info("Creating Vertex AI LLM for endpoint: %s", endpoint)
    llm: Runnable[Any, AIMessage] = ChatVertexAI(
        model_name=endpoint,
        project=settings.vertex_project_id,
        location=settings.vertex_region,
        temperature=temperature,
        api_key=settings.vertex_api_key or None,
    )
    return llm


class _MockJudgeLLM(Runnable[Any, AIMessage]):
    """Mock judge LLM that returns synthetic structured JSON.

    Used when mock_mode=True so the pipeline runs without OpenRouter credentials.
    """

    def __init__(self, model_name: str = "mock-judge"):
        super().__init__()
        self.model_name = model_name

    def invoke(  # noqa: A002
        self, input: Any, config: RunnableConfig | None = None, **kwargs: Any
    ) -> AIMessage:
        logger.info("[MOCK] OpenRouter judge '%s' invoked", self.model_name)
        return AIMessage(content="[MOCK] Judge response placeholder.")

    async def ainvoke(  # noqa: A002
        self, input: Any, config: RunnableConfig | None = None, **kwargs: Any
    ) -> AIMessage:
        return self.invoke(input, config, **kwargs)


def get_openrouter_llm(
    model: str = "anthropic/claude-sonnet-4-6",
    temperature: float = 0.1,
    mock_mode: bool | None = None,
) -> Runnable:
    """Get an OpenRouter LLM for judge evaluation.

    Uses ChatOpenAI pointed at OpenRouter's OpenAI-compatible API.

    Args:
        model: OpenRouter model ID (e.g. "anthropic/claude-sonnet-4-6").
        temperature: Sampling temperature.
        mock_mode: Override mock mode. None = use settings.fine_tuning_mock_mode.

    Returns:
        A Runnable that returns AIMessage.
    """
    settings = get_settings()
    use_mock = mock_mode if mock_mode is not None else settings.fine_tuning_mock_mode

    if use_mock:
        logger.info("Using mock OpenRouter LLM (mock_mode=True)")
        return _MockJudgeLLM(model_name=model)

    api_key = settings.openrouter_api_key
    if not api_key:
        raise ValueError("openrouter_api_key must be set when mock_mode=False")

    try:
        from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "langchain-openai is required for OpenRouter judge models. "
            "Install with: poetry install --with fine-tuning"
        ) from exc

    logger.info("Creating OpenRouter LLM: %s", model)
    llm: Runnable[Any, AIMessage] = ChatOpenAI(
        model=model,
        temperature=temperature,
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    return llm


def get_openrouter_structured_llm(
    schema: type[BaseModel],
    model: str = "anthropic/claude-sonnet-4-6",
    temperature: float = 0.1,
    mock_mode: bool | None = None,
) -> Runnable:
    """Get an OpenRouter LLM with structured output (JSON schema mode).

    Args:
        schema: Pydantic model class for structured output.
        model: OpenRouter model ID.
        temperature: Sampling temperature.
        mock_mode: Override mock mode. None = use settings.fine_tuning_mock_mode.

    Returns:
        A Runnable that returns the schema instance.
    """
    settings = get_settings()
    use_mock = mock_mode if mock_mode is not None else settings.fine_tuning_mock_mode

    if use_mock:
        return get_openrouter_llm(model, temperature, mock_mode=True)

    api_key = settings.openrouter_api_key
    if not api_key:
        raise ValueError("openrouter_api_key must be set when mock_mode=False")

    try:
        from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "langchain-openai is required for OpenRouter judge models. "
            "Install with: poetry install --with fine-tuning"
        ) from exc

    chat_llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    return chat_llm.with_structured_output(schema, method="json_schema")
