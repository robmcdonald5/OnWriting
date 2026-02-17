"""Tests for Style Editor agent."""

from unittest.mock import MagicMock, patch

from ai_writer.agents.style_editor import run_style_editor
from ai_writer.schemas.characters import (
    CharacterProfile,
    CharacterRole,
    CharacterRoster,
)
from ai_writer.schemas.editing import EditFeedback
from ai_writer.schemas.story import Genre, StoryBrief, ToneProfile
from ai_writer.schemas.structure import ActOutline, SceneOutline, StoryOutline
from ai_writer.schemas.writing import SceneDraft


def _build_state():
    return {
        "user_prompt": "Test",
        "story_brief": StoryBrief(
            title="Test",
            premise="A story",
            genre=Genre.SCI_FI,
            themes=["hope"],
            tone_profile=ToneProfile(formality=0.5, darkness=0.3),
        ),
        "character_roster": CharacterRoster(
            characters=[
                CharacterProfile(
                    character_id="c1",
                    name="Captain",
                    role=CharacterRole.PROTAGONIST,
                    voice_notes="calm",
                )
            ]
        ),
        "story_outline": StoryOutline(
            acts=[
                ActOutline(
                    act_number=1,
                    scenes=[
                        SceneOutline(
                            scene_id="s1",
                            act_number=1,
                            scene_number=1,
                            characters_present=["c1"],
                        ),
                    ],
                )
            ]
        ),
        "scene_drafts": [
            SceneDraft(
                scene_id="s1",
                act_number=1,
                scene_number=1,
                prose="The captain stared.",
                word_count=3,
                characters_used=["c1"],
            )
        ],
        "edit_feedback": [],
        "current_scene_index": 0,
    }


class TestStyleEditor:
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    @patch("ai_writer.agents.style_editor.get_settings")
    def test_returns_edit_feedback(self, mock_settings, mock_get_llm):
        mock_settings.return_value = MagicMock(planning_temperature=0.3)

        mock_feedback = EditFeedback(
            scene_id="s1",
            quality_score=0.75,
            approved=True,
            overall_assessment="Good scene.",
        )
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_feedback
        mock_get_llm.return_value = mock_llm

        state = _build_state()
        result = run_style_editor(state)

        assert "edit_feedback" in result
        assert len(result["edit_feedback"]) == 1
        assert result["edit_feedback"][0].scene_id == "s1"
        assert result["edit_feedback"][0].approved is True
