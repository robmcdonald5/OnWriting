"""Foundation schemas for story briefs and configuration."""

from enum import Enum

from pydantic import BaseModel, Field


class Genre(str, Enum):
    """Supported story genres."""

    FANTASY = "fantasy"
    SCI_FI = "sci_fi"
    LITERARY_FICTION = "literary_fiction"
    MYSTERY = "mystery"
    THRILLER = "thriller"
    ROMANCE = "romance"
    HORROR = "horror"
    HISTORICAL_FICTION = "historical_fiction"


class ToneProfile(BaseModel):
    """Numeric tone axes for unambiguous, actionable feedback."""

    formality: float = Field(
        default=0.5, ge=0.0, le=1.0, description="0=casual, 1=formal"
    )
    darkness: float = Field(
        default=0.5, ge=0.0, le=1.0, description="0=lighthearted, 1=dark"
    )
    humor: float = Field(default=0.3, ge=0.0, le=1.0, description="0=serious, 1=comic")
    pacing: float = Field(
        default=0.5, ge=0.0, le=1.0, description="0=slow/contemplative, 1=fast/action"
    )
    prose_style: str = Field(
        default="",
        description="Freeform prose style description (e.g. 'sparse and punchy')",
    )
    reference_authors: list[str] = Field(
        default_factory=list,
        description="Authors whose style should influence tone",
    )


class ScopeParameters(BaseModel):
    """Controls for story length and structure."""

    target_word_count: int = Field(default=3000, gt=0)
    num_acts: int = Field(default=1, ge=1, le=5)
    scenes_per_act: int = Field(default=3, ge=1, le=10)
    target_scene_word_count: int = Field(default=1000, gt=0)


class StoryBrief(BaseModel):
    """The refined creative brief that drives all downstream agents."""

    title: str = Field(min_length=1)
    premise: str = Field(min_length=1)
    genre: Genre
    themes: list[str] = Field(default_factory=list, min_length=1)
    setting_summary: str = Field(default="")
    tone_profile: ToneProfile = Field(default_factory=ToneProfile)
    scope: ScopeParameters = Field(default_factory=ScopeParameters)
    target_audience: str = Field(default="general adult")
