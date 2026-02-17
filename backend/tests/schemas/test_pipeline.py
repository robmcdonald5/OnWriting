"""Tests for pipeline state schema."""

import pytest
from pydantic import ValidationError

from ai_writer.schemas.characters import (
    CharacterProfile,
    CharacterRole,
    CharacterRoster,
)
from ai_writer.schemas.editing import EditFeedback
from ai_writer.schemas.pipeline import PipelineState
from ai_writer.schemas.story import Genre, StoryBrief
from ai_writer.schemas.structure import StoryOutline
from ai_writer.schemas.world import WorldContext
from ai_writer.schemas.writing import SceneDraft


class TestPipelineState:
    def test_init_with_just_prompt(self):
        state = PipelineState(user_prompt="Write me a sci-fi story")
        assert state.user_prompt == "Write me a sci-fi story"
        assert state.story_brief is None
        assert state.scene_drafts == []
        assert state.current_stage == "planning"

    def test_empty_prompt_rejected(self):
        with pytest.raises(ValidationError):
            PipelineState(user_prompt="")

    def test_incremental_field_population(self):
        state = PipelineState(user_prompt="A story about space")

        # Simulate Plot Architect output
        state.story_brief = StoryBrief(
            title="Stars",
            premise="Astronauts discover alien life",
            genre=Genre.SCI_FI,
            themes=["first contact"],
        )
        assert state.story_brief.title == "Stars"

        # Simulate Casting Director output
        state.character_roster = CharacterRoster(
            characters=[
                CharacterProfile(
                    character_id="c1",
                    name="Captain",
                    role=CharacterRole.PROTAGONIST,
                )
            ]
        )
        assert len(state.character_roster.characters) == 1

        # Simulate World Builder output
        state.world_context = WorldContext(setting_period="2350 AD")
        assert state.world_context.setting_period == "2350 AD"

        # Simulate Beat Outliner output
        state.story_outline = StoryOutline()
        assert state.story_outline.total_scenes == 0

        # Simulate Scene Writer output
        state.scene_drafts.append(
            SceneDraft(scene_id="s1", act_number=1, scene_number=1, word_count=800)
        )
        assert len(state.scene_drafts) == 1

        # Simulate Editor output
        state.edit_feedback.append(
            EditFeedback(scene_id="s1", quality_score=0.8, approved=True)
        )
        assert state.edit_feedback[0].approved is True

    def test_control_flow_defaults(self):
        state = PipelineState(user_prompt="test")
        assert state.current_scene_index == 0
        assert state.revision_count == 0
        assert state.max_revisions == 2
        assert state.errors == []
