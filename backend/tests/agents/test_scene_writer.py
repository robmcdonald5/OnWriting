"""Tests for Scene Writer agent."""

from unittest.mock import MagicMock, patch

from ai_writer.agents.scene_writer import run_scene_writer
from ai_writer.schemas.characters import (
    CharacterProfile,
    CharacterRole,
    CharacterRoster,
)
from ai_writer.schemas.editing import EditFeedback
from ai_writer.schemas.story import Genre, StoryBrief, ToneProfile
from ai_writer.schemas.structure import ActOutline, SceneOutline, StoryOutline


def _build_state(revision_count=0, existing_drafts=None, edit_feedback=None):
    return {
        "user_prompt": "Test prompt",
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
                    voice_notes="calm and measured",
                    speech_patterns=["I see"],
                    motivation="Find the truth",
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
                            scene_goal="Establish setting",
                            target_word_count=1000,
                        ),
                    ],
                )
            ]
        ),
        "current_scene_index": 0,
        "revision_count": revision_count,
        "scene_drafts": existing_drafts or [],
        "edit_feedback": edit_feedback or [],
    }


class TestSceneWriter:
    @patch("ai_writer.agents.scene_writer.get_llm")
    @patch("ai_writer.agents.scene_writer.get_settings")
    def test_produces_scene_draft(self, mock_settings, mock_get_llm):
        mock_settings.return_value = MagicMock(default_temperature=0.7)

        mock_response = MagicMock()
        mock_response.content = (
            "The station hummed quietly as Captain stood by the viewport."
        )
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        state = _build_state()
        result = run_scene_writer(state)

        assert "scene_drafts" in result
        assert len(result["scene_drafts"]) == 1
        assert result["scene_drafts"][0].scene_id == "s1"
        assert result["scene_drafts"][0].word_count > 0

    @patch("ai_writer.agents.scene_writer.get_llm")
    @patch("ai_writer.agents.scene_writer.get_settings")
    def test_revision_replaces_last_draft(self, mock_settings, mock_get_llm):
        mock_settings.return_value = MagicMock(default_temperature=0.7)

        mock_response = MagicMock()
        mock_response.content = "Revised scene prose."
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        from ai_writer.schemas.writing import SceneDraft

        existing = [
            SceneDraft(
                scene_id="s1", act_number=1, scene_number=1, prose="Old.", word_count=1
            )
        ]
        feedback = [
            EditFeedback(
                scene_id="s1",
                quality_score=0.5,
                approved=False,
                revision_instructions="Improve pacing",
            )
        ]

        state = _build_state(
            revision_count=1, existing_drafts=existing, edit_feedback=feedback
        )
        result = run_scene_writer(state)

        assert len(result["scene_drafts"]) == 1
        assert result["scene_drafts"][0].prose == "Revised scene prose."
