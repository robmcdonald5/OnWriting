"""Tests for the LLM factory (Vertex + OpenRouter)."""

from langchain_core.messages import AIMessage, HumanMessage

from ai_writer.fine_tuning.llm import (
    _MockJudgeLLM,
    _MockTunedLLM,
    get_openrouter_llm,
    get_openrouter_structured_llm,
    get_vertex_llm,
)


class TestVertexLLM:
    def test_mock_mode_returns_mock(self):
        llm = get_vertex_llm(mock_mode=True)
        assert isinstance(llm, _MockTunedLLM)

    def test_mock_invoke_returns_ai_message(self):
        llm = get_vertex_llm(mock_mode=True)
        result = llm.invoke([HumanMessage(content="test")])
        assert isinstance(result, AIMessage)
        assert len(result.content) > 0


class TestOpenRouterLLM:
    def test_mock_mode_returns_mock(self):
        llm = get_openrouter_llm(mock_mode=True)
        assert isinstance(llm, _MockJudgeLLM)

    def test_mock_invoke_returns_ai_message(self):
        llm = get_openrouter_llm(mock_mode=True)
        result = llm.invoke([HumanMessage(content="test")])
        assert isinstance(result, AIMessage)

    def test_mock_model_name_preserved(self):
        llm = get_openrouter_llm(model="openai/gpt-4.1", mock_mode=True)
        assert isinstance(llm, _MockJudgeLLM)
        assert llm.model_name == "openai/gpt-4.1"

    def test_structured_mock_returns_mock_llm(self):
        """Structured output in mock mode returns the base mock LLM."""
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            value: str = ""

        llm = get_openrouter_structured_llm(TestSchema, mock_mode=True)
        assert isinstance(llm, _MockJudgeLLM)
