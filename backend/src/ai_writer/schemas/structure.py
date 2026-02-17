"""Structural decomposition schemas — the most critical file.

These schemas force the planning agents to produce unambiguous, detailed
outlines so that Scene Writers make zero plot decisions.
"""

from enum import Enum

from pydantic import BaseModel, Field, computed_field


class BeatType(str, Enum):
    """Standard narrative beat types."""

    HOOK = "hook"
    INCITING_INCIDENT = "inciting_incident"
    RISING_ACTION = "rising_action"
    MIDPOINT = "midpoint"
    COMPLICATION = "complication"
    CRISIS = "crisis"
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"


class EmotionalValence(str, Enum):
    """Emotional direction of a beat."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class NarrativeBeat(BaseModel):
    """A single narrative beat within the story structure."""

    beat_id: str = Field(min_length=1)
    act_number: int = Field(ge=1)
    sequence_number: int = Field(ge=1)
    beat_type: BeatType
    summary: str = Field(min_length=1)
    characters_involved: list[str] = Field(default_factory=list)
    location_id: str = Field(default="")
    emotional_valence: EmotionalValence = EmotionalValence.NEUTRAL
    purpose: str = Field(
        default="",
        description="What this beat accomplishes for the story",
    )


class SceneOutline(BaseModel):
    """Comprehensive scene outline — deliberately detailed so the Scene Writer
    makes zero plot decisions.
    """

    scene_id: str = Field(min_length=1)
    act_number: int = Field(ge=1)
    scene_number: int = Field(ge=1)
    title: str = Field(default="")
    beat_ids: list[str] = Field(default_factory=list)
    setting: str = Field(default="")
    characters_present: list[str] = Field(default_factory=list)
    pov_character_id: str = Field(default="")
    scene_goal: str = Field(default="")
    emotional_arc: str = Field(
        default="",
        description="e.g. 'tension builds from curiosity to dread'",
    )
    opening_hook: str = Field(default="")
    closing_image: str = Field(default="")
    key_dialogue_beats: list[str] = Field(default_factory=list)
    prior_scene_summary: str = Field(
        default="",
        description="Rolling context — summary of what happened before this scene",
    )
    target_word_count: int = Field(default=1000, gt=0)


class ActOutline(BaseModel):
    """Outline for a single act, containing beats and scenes."""

    act_number: int = Field(ge=1)
    title: str = Field(default="")
    summary: str = Field(default="")
    themes_explored: list[str] = Field(default_factory=list)
    beats: list[NarrativeBeat] = Field(default_factory=list)
    scenes: list[SceneOutline] = Field(default_factory=list)


class StoryOutline(BaseModel):
    """The complete structural outline for the story."""

    acts: list[ActOutline] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_scenes(self) -> int:
        """Total number of scenes across all acts."""
        return sum(len(act.scenes) for act in self.acts)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_beats(self) -> int:
        """Total number of narrative beats across all acts."""
        return sum(len(act.beats) for act in self.acts)
