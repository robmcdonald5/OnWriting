"""LangGraph pipeline state schema."""

from pydantic import BaseModel, Field

from ai_writer.schemas.characters import CharacterRoster
from ai_writer.schemas.editing import EditFeedback
from ai_writer.schemas.story import StoryBrief
from ai_writer.schemas.structure import StoryOutline
from ai_writer.schemas.world import WorldContext
from ai_writer.schemas.writing import SceneDraft


class PipelineState(BaseModel):
    """Accumulating state for the LangGraph prototype pipeline.

    Only `user_prompt` is required at initialization. All other fields
    are populated by agents as the pipeline progresses.
    """

    # Input
    user_prompt: str = Field(min_length=1)

    # Accumulated by agents
    story_brief: StoryBrief | None = None
    character_roster: CharacterRoster | None = None
    world_context: WorldContext | None = None
    story_outline: StoryOutline | None = None
    scene_drafts: list[SceneDraft] = Field(default_factory=list)
    edit_feedback: list[EditFeedback] = Field(default_factory=list)

    # Control flow
    current_scene_index: int = Field(default=0, ge=0)
    revision_count: int = Field(default=0, ge=0)
    max_revisions: int = Field(default=2, ge=0)
    min_revisions: int = Field(default=1, ge=0)
    current_stage: str = Field(default="planning")
    errors: list[str] = Field(default_factory=list)
