"""Tests for Scene Writer agent."""

from unittest.mock import MagicMock, patch

from ai_writer.agents.scene_writer import run_scene_writer
from ai_writer.schemas.characters import (
    CharacterProfile,
    CharacterRole,
    CharacterRoster,
)
from ai_writer.schemas.editing import EditFeedback, SceneRubric
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
                rubric=SceneRubric(
                    style_adherence=2,
                    character_voice=1,
                    outline_adherence=3,
                    pacing=2,
                    prose_quality=2,
                ),
            )
        ]

        state = _build_state(
            revision_count=1, existing_drafts=existing, edit_feedback=feedback
        )
        result = run_scene_writer(state)

        assert len(result["scene_drafts"]) == 1
        assert result["scene_drafts"][0].prose == "Revised scene prose."

    @patch("ai_writer.agents.scene_writer.get_llm")
    @patch("ai_writer.agents.scene_writer.get_settings")
    def test_revision_includes_dimension_breakdown(self, mock_settings, mock_get_llm):
        """Verify the revision addendum includes per-dimension scores."""
        mock_settings.return_value = MagicMock(default_temperature=0.7)

        mock_response = MagicMock()
        mock_response.content = "Revised prose with better voice."
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        from ai_writer.schemas.writing import SceneDraft

        existing = [
            SceneDraft(
                scene_id="s1",
                act_number=1,
                scene_number=1,
                prose="Old.",
                word_count=1,
            )
        ]
        feedback = [
            EditFeedback(
                scene_id="s1",
                quality_score=0.5,
                approved=False,
                revision_instructions="Character voice needs work.",
                rubric=SceneRubric(
                    style_adherence=2,
                    character_voice=1,
                    outline_adherence=3,
                    pacing=2,
                    prose_quality=2,
                ),
            )
        ]

        state = _build_state(
            revision_count=1, existing_drafts=existing, edit_feedback=feedback
        )
        run_scene_writer(state)

        # Verify the LLM was called with dimension info in the system prompt
        call_args = mock_llm.invoke.call_args[0][0]
        system_msg = call_args[0]["content"]
        assert "style=2/4" in system_msg
        assert "voice=1/4" in system_msg
        assert "character_voice (scored 1/4)" in system_msg
        assert "CRITICAL" in system_msg

    @patch("ai_writer.agents.scene_writer.get_llm")
    @patch("ai_writer.agents.scene_writer.get_settings")
    def test_revision_includes_confirmed_slop(self, mock_settings, mock_get_llm):
        """Verify confirmed slop phrases are forwarded in revision prompt."""
        mock_settings.return_value = MagicMock(default_temperature=0.7)

        mock_response = MagicMock()
        mock_response.content = "Revised prose."
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        from ai_writer.schemas.writing import SceneDraft

        existing = [
            SceneDraft(
                scene_id="s1",
                act_number=1,
                scene_number=1,
                prose="Old.",
                word_count=1,
            )
        ]
        feedback = [
            EditFeedback(
                scene_id="s1",
                quality_score=0.5,
                approved=False,
                revision_instructions="Fix AI-isms.",
                confirmed_slop=["testament to", "tapestry of"],
                rubric=SceneRubric(
                    style_adherence=2,
                    character_voice=2,
                    outline_adherence=2,
                    pacing=2,
                    prose_quality=1,
                ),
            )
        ]

        state = _build_state(
            revision_count=1, existing_drafts=existing, edit_feedback=feedback
        )
        run_scene_writer(state)

        call_args = mock_llm.invoke.call_args[0][0]
        system_msg = call_args[0]["content"]
        assert "testament to" in system_msg
        assert "tapestry of" in system_msg
        assert "REPLACE" in system_msg

    @patch("ai_writer.agents.scene_writer.get_llm")
    @patch("ai_writer.agents.scene_writer.get_settings")
    def test_revision_includes_structural_issues(self, mock_settings, mock_get_llm):
        """Verify structural issues are forwarded in revision prompt."""
        mock_settings.return_value = MagicMock(default_temperature=0.7)

        mock_response = MagicMock()
        mock_response.content = "Revised prose with varied structure."
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        from ai_writer.schemas.writing import SceneDraft

        existing = [
            SceneDraft(
                scene_id="s1",
                act_number=1,
                scene_number=1,
                prose="Old.",
                word_count=1,
            )
        ]
        feedback = [
            EditFeedback(
                scene_id="s1",
                quality_score=0.5,
                approved=False,
                revision_instructions="Vary sentence structure.",
                rubric=SceneRubric(
                    style_adherence=2,
                    character_voice=2,
                    outline_adherence=2,
                    pacing=2,
                    prose_quality=2,
                    opener_monotony=True,
                    low_diversity=True,
                ),
            )
        ]

        state = _build_state(
            revision_count=1, existing_drafts=existing, edit_feedback=feedback
        )
        run_scene_writer(state)

        call_args = mock_llm.invoke.call_args[0][0]
        system_msg = call_args[0]["content"]
        assert "VARY" in system_msg
        assert "monotonous" in system_msg.lower() or "openings" in system_msg.lower()
        assert "diversity" in system_msg.lower() or "vocabulary" in system_msg.lower()

    @patch("ai_writer.agents.scene_writer.get_llm")
    @patch("ai_writer.agents.scene_writer.get_settings")
    def test_polish_addendum_used_when_approved(self, mock_settings, mock_get_llm):
        """When draft was approved but forced-revised, use POLISH PASS not REVISION."""
        mock_settings.return_value = MagicMock(default_temperature=0.7)

        mock_response = MagicMock()
        mock_response.content = "Polished prose."
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        from ai_writer.schemas.writing import SceneDraft

        existing = [
            SceneDraft(
                scene_id="s1",
                act_number=1,
                scene_number=1,
                prose="Great first draft.",
                word_count=4,
            )
        ]
        feedback = [
            EditFeedback(
                scene_id="s1",
                quality_score=0.85,
                approved=True,
                revision_instructions="Minor polish suggestions.",
                rubric=SceneRubric(
                    style_adherence=4,
                    character_voice=3,
                    outline_adherence=4,
                    pacing=3,
                    prose_quality=3,
                ),
            )
        ]

        state = _build_state(
            revision_count=1, existing_drafts=existing, edit_feedback=feedback
        )
        run_scene_writer(state)

        call_args = mock_llm.invoke.call_args[0][0]
        system_msg = call_args[0]["content"]
        assert "POLISH PASS" in system_msg
        assert "approved" in system_msg.lower()
        assert "REVISION INSTRUCTIONS" not in system_msg

    @patch("ai_writer.agents.scene_writer.get_llm")
    @patch("ai_writer.agents.scene_writer.get_settings")
    def test_revision_addendum_used_when_not_approved(
        self, mock_settings, mock_get_llm
    ):
        """When draft failed QA, use REVISION INSTRUCTIONS not POLISH PASS."""
        mock_settings.return_value = MagicMock(default_temperature=0.7)

        mock_response = MagicMock()
        mock_response.content = "Revised prose."
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        from ai_writer.schemas.writing import SceneDraft

        existing = [
            SceneDraft(
                scene_id="s1",
                act_number=1,
                scene_number=1,
                prose="Weak draft.",
                word_count=2,
            )
        ]
        feedback = [
            EditFeedback(
                scene_id="s1",
                quality_score=0.45,
                approved=False,
                revision_instructions="Major pacing and voice issues.",
                rubric=SceneRubric(
                    style_adherence=2,
                    character_voice=1,
                    outline_adherence=2,
                    pacing=2,
                    prose_quality=2,
                ),
            )
        ]

        state = _build_state(
            revision_count=1, existing_drafts=existing, edit_feedback=feedback
        )
        run_scene_writer(state)

        call_args = mock_llm.invoke.call_args[0][0]
        system_msg = call_args[0]["content"]
        assert "REVISION INSTRUCTIONS" in system_msg
        assert "POLISH PASS" not in system_msg
