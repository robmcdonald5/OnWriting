"""Editor feedback schemas for the revision loop.

Two-tier schema design:
- StyleEditorOutput: Flat model the LLM fills (Gemini-compatible).
- SceneRubric: Full rubric combining deterministic checks + LLM dimensions.
- EditFeedback: Top-level feedback container with rubric and computed scores.
- SceneMetrics: Per-scene metrics for trend tracking.
"""

from enum import Enum

from pydantic import BaseModel, Field


class EditType(str, Enum):
    """Categories of editorial feedback."""

    STYLE = "style"
    CONTINUITY = "continuity"
    CHARACTER_VOICE = "character_voice"
    PACING = "pacing"
    CLARITY = "clarity"
    GRAMMAR = "grammar"
    PLOT_HOLE = "plot_hole"


class EditSeverity(str, Enum):
    """How strongly the editor recommends the change."""

    SUGGESTION = "suggestion"
    RECOMMENDED = "recommended"
    REQUIRED = "required"


class EditItem(BaseModel):
    """A single editorial note."""

    edit_type: EditType
    severity: EditSeverity
    location_hint: str = Field(
        default="",
        description="Approximate location in the prose (e.g. 'paragraph 3')",
    )
    original_text: str = Field(default="")
    suggested_text: str = Field(default="")
    rationale: str = Field(default="")


# --- LLM Output Schema (kept flat for Gemini compatibility) ---


class StyleEditorOutput(BaseModel):
    """What the LLM returns — kept flat for Gemini structured output.

    Field ordering matters: dimension_reasoning comes FIRST so the LLM
    commits to a critique before assigning scores (critique-before-score).
    With method="json_schema" Gemini fills fields in declaration order.
    """

    dimension_reasoning: str = Field(
        description="Evidence-based reasoning for each dimension score"
    )
    style_adherence: int = Field(ge=1, le=4)
    character_voice: int = Field(ge=1, le=4)
    outline_adherence: int = Field(ge=1, le=4)
    pacing: int = Field(ge=1, le=4)
    prose_quality: int = Field(ge=1, le=4)
    confirmed_slop: list[str] = Field(
        default_factory=list,
        description=(
            "Phrases from Flagged Phrases confirmed as genuine AI-isms (exact quotes)"
        ),
    )
    revision_instructions: str = Field(
        default="",
        description="Specific revision instructions if quality is insufficient",
    )
    overall_assessment: str = Field(default="")


# --- Rubric with Deterministic + LLM Dimensions ---

# Weights for composite score calculation
DIMENSION_WEIGHTS: dict[str, float] = {
    "style_adherence": 0.20,
    "character_voice": 0.20,
    "outline_adherence": 0.20,
    "pacing": 0.20,
    "prose_quality": 0.20,
}

APPROVE_THRESHOLD = 0.7


class SceneRubric(BaseModel):
    """Full rubric combining deterministic checks and LLM dimension scores.

    Deterministic checks are filled by Python code (zero LLM cost).
    Dimension scores are filled from StyleEditorOutput (1 LLM call).
    Composite score and approval are computed algorithmically.
    """

    # --- Deterministic checks (filled by Python) ---
    word_count_in_range: bool = Field(default=True)
    tense_consistent: bool = Field(default=True)
    slop_ratio: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="1.0 = clean, 0.0 = heavy slop",
    )

    # --- Dimension scores (filled from LLM output, 1-4 scale) ---
    style_adherence: int = Field(default=2, ge=1, le=4)
    character_voice: int = Field(default=2, ge=1, le=4)
    outline_adherence: int = Field(default=2, ge=1, le=4)
    pacing: int = Field(default=2, ge=1, le=4)
    prose_quality: int = Field(default=2, ge=1, le=4)

    # --- Structural analysis (advisory, soft penalty) ---
    opener_monotony: bool = Field(default=False)
    length_monotony: bool = Field(default=False)
    passive_heavy: bool = Field(default=False)
    structural_monotony: bool = Field(default=False)

    # --- Vocabulary analysis (advisory, soft penalty) ---
    low_diversity: bool = Field(default=False)
    vocabulary_basic: bool = Field(default=False)

    # --- Cross-scene analysis ---
    cross_scene_repetitions: int = Field(default=0)

    # --- Chain-of-thought reasoning ---
    dimension_reasoning: str = Field(default="")

    def compute_quality_score(self) -> float:
        """Weighted average of dimension scores, normalized to 0-1.

        Each dimension is scored 1-4, so we normalize:
        (weighted_sum - 1) / (4 - 1) maps [1, 4] -> [0, 1].

        Advisory metrics apply a soft penalty (max 0.18 + 0.06 cross-scene).
        """
        dimensions = {
            "style_adherence": self.style_adherence,
            "character_voice": self.character_voice,
            "outline_adherence": self.outline_adherence,
            "pacing": self.pacing,
            "prose_quality": self.prose_quality,
        }

        weighted_sum = sum(
            dimensions[dim] * DIMENSION_WEIGHTS[dim] for dim in dimensions
        )
        # Normalize: min possible = 1.0, max possible = 4.0
        normalized = (weighted_sum - 1.0) / 3.0

        # Soft penalty for advisory metrics (max 0.18)
        advisory_penalty = 0.0
        if self.opener_monotony:
            advisory_penalty += 0.04
        if self.length_monotony:
            advisory_penalty += 0.04
        if self.passive_heavy:
            advisory_penalty += 0.02
        if self.structural_monotony:
            advisory_penalty += 0.02
        if self.low_diversity:
            advisory_penalty += 0.04
        if self.vocabulary_basic:
            advisory_penalty += 0.02

        # Cross-scene repetition penalty (max 0.06)
        advisory_penalty += 0.02 * min(self.cross_scene_repetitions, 3)

        return round(max(0.0, min(1.0, normalized - advisory_penalty)), 2)

    def has_critical_failure(self) -> bool:
        """Any dimension at 1/4 is a critical failure requiring revision."""
        return any(
            score <= 1
            for score in [
                self.style_adherence,
                self.character_voice,
                self.outline_adherence,
                self.pacing,
                self.prose_quality,
            ]
        )

    def compute_approved(self) -> bool:
        """Composite approval: score >= threshold AND no critical failures
        AND deterministic checks pass.
        """
        score_ok = self.compute_quality_score() >= APPROVE_THRESHOLD
        no_critical = not self.has_critical_failure()
        deterministic_ok = self.word_count_in_range and self.tense_consistent
        return score_ok and no_critical and deterministic_ok

    def dimension_summary(self) -> str:
        """One-line summary of all dimension scores."""
        return (
            f"style={self.style_adherence}/4 "
            f"voice={self.character_voice}/4 "
            f"outline={self.outline_adherence}/4 "
            f"pacing={self.pacing}/4 "
            f"prose={self.prose_quality}/4"
        )


class EditFeedback(BaseModel):
    """Complete editorial feedback for a scene."""

    scene_id: str = Field(min_length=1)
    editor_name: str = Field(default="style_editor")
    edits: list[EditItem] = Field(default_factory=list)
    overall_assessment: str = Field(default="")
    quality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Computed from rubric dimensions, not LLM-assigned",
    )
    approved: bool = Field(default=False)
    revision_instructions: str = Field(
        default="",
        description="High-level instructions for the writer if revision is needed",
    )
    confirmed_slop: list[str] = Field(default_factory=list)
    rubric: SceneRubric = Field(default_factory=SceneRubric)


class SceneMetrics(BaseModel):
    """Per-scene metrics snapshot for trend tracking."""

    scene_id: str
    slop_ratio: float
    mtld: float
    opener_ratio: float
    sent_length_cv: float
    word_count: int
