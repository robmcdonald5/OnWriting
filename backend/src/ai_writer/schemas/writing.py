"""Writer output schemas for scene and act drafts."""

from pydantic import BaseModel, Field, computed_field


class SceneDraft(BaseModel):
    """Raw prose output from the Scene Writer."""

    scene_id: str = Field(min_length=1)
    act_number: int = Field(ge=1)
    scene_number: int = Field(ge=1)
    prose: str = Field(default="")
    word_count: int = Field(default=0, ge=0)
    characters_used: list[str] = Field(default_factory=list)
    scene_summary: str = Field(
        default="",
        description="Brief summary for rolling context to subsequent scenes",
    )
    notes_for_editor: str = Field(
        default="",
        description="Writer's notes about areas needing attention",
    )


class ActDraft(BaseModel):
    """Collection of scene drafts forming an act."""

    act_number: int = Field(ge=1)
    scenes: list[SceneDraft] = Field(default_factory=list)
    act_summary: str = Field(default="")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_word_count(self) -> int:
        """Sum of word counts across all scenes in this act."""
        return sum(s.word_count for s in self.scenes)
