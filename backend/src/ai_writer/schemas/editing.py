"""Editor feedback schemas for the revision loop."""

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
        description="0.0=needs complete rewrite, 1.0=publish-ready",
    )
    approved: bool = Field(default=False)
    revision_instructions: str = Field(
        default="",
        description="High-level instructions for the writer if revision is needed",
    )
