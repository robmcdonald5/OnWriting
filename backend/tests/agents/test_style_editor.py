"""Tests for Style Editor agent."""

from unittest.mock import MagicMock, patch

from ai_writer.agents.style_editor import run_style_editor
from ai_writer.schemas.characters import (
    CharacterProfile,
    CharacterRole,
    CharacterRoster,
)
from ai_writer.schemas.editing import StyleEditorOutput
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
                            target_word_count=100,
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
                prose="The captain stared at the viewport. Stars drifted past in silence.",
                word_count=11,
                characters_used=["c1"],
            )
        ],
        "edit_feedback": [],
        "current_scene_index": 0,
    }


class TestStyleEditor:
    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_returns_edit_feedback_with_rubric(self, mock_get_llm, mock_invoke):
        mock_output = StyleEditorOutput(
            style_adherence=2,
            character_voice=2,
            outline_adherence=3,
            pacing=2,
            prose_quality=2,
            dimension_reasoning="Style matches tone axes mostly.",
            overall_assessment="Decent first draft.",
            revision_instructions="Improve character voice.",
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        result = run_style_editor(state)

        assert "edit_feedback" in result
        assert len(result["edit_feedback"]) == 1

        fb = result["edit_feedback"][0]
        assert fb.scene_id == "s1"
        assert fb.rubric.style_adherence == 2
        assert fb.rubric.outline_adherence == 3
        assert fb.quality_score == fb.rubric.compute_quality_score()
        assert fb.approved == fb.rubric.compute_approved()

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_critical_failure_prevents_approval(self, mock_get_llm, mock_invoke):
        mock_output = StyleEditorOutput(
            style_adherence=3,
            character_voice=1,  # critical failure
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
            dimension_reasoning="Voice is weak.",
            revision_instructions="Characters sound interchangeable.",
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        result = run_style_editor(state)

        fb = result["edit_feedback"][0]
        assert fb.rubric.has_critical_failure() is True
        assert fb.approved is False

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_all_threes_approves(self, mock_get_llm, mock_invoke):
        mock_output = StyleEditorOutput(
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
            dimension_reasoning="Excellent across all dimensions.",
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        # Use prose that's within word count tolerance (100 target, +/-25%)
        state = _build_state()
        state["scene_drafts"][0].prose = " ".join(["word"] * 100)
        state["scene_drafts"][0].word_count = 100

        result = run_style_editor(state)

        fb = result["edit_feedback"][0]
        assert fb.quality_score == 1.0
        assert fb.approved is True

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_deterministic_checks_incorporated(self, mock_get_llm, mock_invoke):
        """Verify deterministic results are stored in the rubric."""
        mock_output = StyleEditorOutput(
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
            dimension_reasoning="All good.",
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        # Prose is 11 words vs target 100 — should fail word count check
        result = run_style_editor(state)

        fb = result["edit_feedback"][0]
        assert fb.rubric.word_count_in_range is False
        # Word count failure should prevent approval even with all 3s
        assert fb.approved is False
