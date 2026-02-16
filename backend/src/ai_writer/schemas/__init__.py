"""Pydantic schemas for agent data contracts."""

from ai_writer.schemas.characters import (
    CharacterProfile,
    CharacterRelationship,
    CharacterRole,
    CharacterRoster,
)
from ai_writer.schemas.editing import EditFeedback, EditItem, EditSeverity, EditType
from ai_writer.schemas.pipeline import PipelineState
from ai_writer.schemas.story import Genre, ScopeParameters, StoryBrief, ToneProfile
from ai_writer.schemas.structure import (
    ActOutline,
    BeatType,
    EmotionalValence,
    NarrativeBeat,
    SceneOutline,
    StoryOutline,
)
from ai_writer.schemas.world import Location, WorldContext, WorldRule
from ai_writer.schemas.writing import ActDraft, SceneDraft

__all__ = [
    # story
    "Genre",
    "ToneProfile",
    "ScopeParameters",
    "StoryBrief",
    # characters
    "CharacterRole",
    "CharacterProfile",
    "CharacterRelationship",
    "CharacterRoster",
    # world
    "Location",
    "WorldRule",
    "WorldContext",
    # structure
    "BeatType",
    "EmotionalValence",
    "NarrativeBeat",
    "SceneOutline",
    "ActOutline",
    "StoryOutline",
    # writing
    "SceneDraft",
    "ActDraft",
    # editing
    "EditType",
    "EditSeverity",
    "EditItem",
    "EditFeedback",
    # pipeline
    "PipelineState",
]
