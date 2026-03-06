"""Configuration models for fine-tuning workflows."""

from typing import Literal

from pydantic import BaseModel, Field


class FineTuningJobConfig(BaseModel):
    """Configuration for a Vertex AI supervised fine-tuning job."""

    source_model: str = Field(
        default="gemini-2.5-flash",
        description="Base model to fine-tune",
    )
    training_data_uri: str = Field(
        default="",
        description="GCS URI of the training JSONL file (gs://bucket/path.jsonl)",
    )
    validation_data_uri: str = Field(
        default="",
        description="GCS URI of validation JSONL file (optional, recommended for overfitting detection)",
    )
    display_name: str = Field(
        default="ai-writer-sft",
        description="Display name for the tuning job in Vertex AI console",
    )
    epochs: int = Field(
        default=4,
        ge=1,
        le=100,
        description="Training epochs. Google recommends 20 for <1k examples",
    )
    adapter_size: Literal[1, 4, 8, 16] = Field(
        default=4,
        description="LoRA adapter size (1, 4, 8, 16). 4 is good for style/tone tasks",
    )
    learning_rate_multiplier: float = Field(
        default=1.0,
        gt=0.0,
        description="Learning rate multiplier. Google recommends 10.0 for <1k examples",
    )


class ComparisonConfig(BaseModel):
    """Configuration for A/B comparison runs."""

    base_model: str = Field(
        default="gemini-2.5-flash",
        description="Base model identifier",
    )
    tuned_model_endpoint: str = Field(
        default="",
        description="Tuned model endpoint (Vertex AI endpoint ID or resource name)",
    )
    judge_model: str = Field(
        default="anthropic/claude-sonnet-4-6",
        description="Model used for LLM-as-judge evaluation (OpenRouter model ID)",
    )
    bidirectional_judge: bool = Field(
        default=True,
        description="Run judge in both A/B orderings per prompt (recommended)",
    )
    judge_models: list[str] = Field(
        default_factory=list,
        description="Additional judge models for cross-validation (run alongside primary judge_model)",
    )
    categories: list[str] = Field(
        default_factory=lambda: ["all"],
        description="Prompt categories to include (or 'all')",
    )
    output_dir: str = Field(
        default="output/comparisons",
        description="Directory for comparison reports",
    )
    temperature: float = Field(
        default=0.7,
        description="Temperature for both models during comparison",
    )
