"""Data models for A/B comparison results."""

from typing import Literal

from pydantic import BaseModel, Field


class ModelOutput(BaseModel):
    """Raw output from a single model invocation."""

    model_id: str
    prompt_id: str
    prompt_category: str
    text: str
    latency_seconds: float = 0.0
    token_count_approx: int = 0
    is_mock: bool = False


class TextAnalysisSnapshot(BaseModel):
    """Deterministic text analysis metrics for a single output."""

    slop_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    slop_phrase_count: int = 0
    mtld: float = 0.0
    mattr: float = 0.0
    mean_word_zipf: float = 0.0
    opener_monotony: bool = False
    top_opener_pos: str = ""
    top_opener_ratio: float = 0.0
    length_monotony: bool = False
    sent_length_cv: float = 0.0
    passive_ratio: float = 0.0
    mean_dep_distance: float = 0.0
    word_count: int = 0


class JudgeVerdict(BaseModel):
    """LLM-as-judge evaluation for a single prompt pair."""

    prompt_id: str
    style_adherence_a: int = Field(ge=1, le=4)
    style_adherence_b: int = Field(ge=1, le=4)
    character_voice_a: int = Field(ge=1, le=4)
    character_voice_b: int = Field(ge=1, le=4)
    outline_adherence_a: int = Field(ge=1, le=4)
    outline_adherence_b: int = Field(ge=1, le=4)
    pacing_a: int = Field(ge=1, le=4)
    pacing_b: int = Field(ge=1, le=4)
    prose_quality_a: int = Field(ge=1, le=4)
    prose_quality_b: int = Field(ge=1, le=4)
    preferred: Literal["A", "B", "tie"] = Field(description="'A', 'B', or 'tie'")
    reasoning: str = ""
    a_is_base: bool = Field(description="True if A=base model, False if A=tuned model")


class PromptComparisonResult(BaseModel):
    """Complete comparison result for a single prompt."""

    prompt_id: str
    prompt_category: str
    prompt_text: str
    system_prompt: str = ""
    base_output: ModelOutput
    tuned_output: ModelOutput
    base_analysis: TextAnalysisSnapshot
    tuned_analysis: TextAnalysisSnapshot
    judge_verdict: JudgeVerdict | None = None


class ComparisonReport(BaseModel):
    """Aggregate comparison report across all prompts."""

    timestamp: str
    base_model: str
    tuned_model: str
    prompt_count: int
    results: list[PromptComparisonResult]

    # Aggregate stats
    base_wins: int = 0
    tuned_wins: int = 0
    ties: int = 0
    mean_slop_delta: float = 0.0
    mean_mtld_delta: float = 0.0
    mean_word_count_delta: float = 0.0
    is_mock: bool = False
