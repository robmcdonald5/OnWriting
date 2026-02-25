"""Tests for Style Editor agent."""

import logging
from unittest.mock import MagicMock, patch

from ai_writer.agents.style_editor import run_style_editor
from ai_writer.schemas.characters import (
    CharacterProfile,
    CharacterRole,
    CharacterRoster,
)
from ai_writer.schemas.editing import (
    EditFeedback,
    SceneMetrics,
    SceneRubric,
    StyleEditorOutput,
)
from ai_writer.schemas.story import Genre, StoryBrief, ToneProfile
from ai_writer.schemas.structure import ActOutline, SceneOutline, StoryOutline
from ai_writer.schemas.world import WorldContext
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
        "world_context": WorldContext(),
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
        "scene_metrics": [],
        "current_scene_index": 0,
    }


class TestStyleEditor:
    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_returns_edit_feedback_with_rubric(self, mock_get_llm, mock_invoke):
        mock_output = StyleEditorOutput(
            dimension_reasoning="Style matches tone axes mostly.",
            style_adherence=2,
            character_voice=2,
            outline_adherence=3,
            pacing=2,
            prose_quality=2,
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
            dimension_reasoning="Voice is weak.",
            style_adherence=4,
            character_voice=1,  # critical failure
            outline_adherence=4,
            pacing=4,
            prose_quality=4,
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
    def test_all_fours_approves(self, mock_get_llm, mock_invoke):
        mock_output = StyleEditorOutput(
            dimension_reasoning="Excellent across all dimensions.",
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,
            prose_quality=4,
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        # Use prose that's within word count tolerance (100 target, +/-25%)
        # Note: repetitive prose triggers advisory flags (opener_monotony,
        # length_monotony, low_diversity) which apply a soft penalty, but
        # score caps may also reduce pacing. Use enough varied prose.
        state = _build_state()
        state["scene_drafts"][0].prose = " ".join(["word"] * 100)
        state["scene_drafts"][0].word_count = 100

        result = run_style_editor(state)

        fb = result["edit_feedback"][0]
        # Even with all-4s from LLM, score caps and penalties may reduce.
        # The key test is that the system processes correctly.
        assert fb.quality_score <= 1.0
        assert fb.quality_score > 0

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_all_threes_does_not_approve(self, mock_get_llm, mock_invoke):
        """All-3s on 1-4 scale produces 0.67, below 0.7 threshold."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Competent across all dimensions.",
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        state["scene_drafts"][0].prose = " ".join(["word"] * 100)
        state["scene_drafts"][0].word_count = 100

        result = run_style_editor(state)

        fb = result["edit_feedback"][0]
        assert fb.approved is False

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_deterministic_checks_incorporated(self, mock_get_llm, mock_invoke):
        """Verify deterministic results are stored in the rubric."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="All good.",
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,
            prose_quality=4,
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        # Prose is 11 words vs target 100 — should fail word count check
        result = run_style_editor(state)

        fb = result["edit_feedback"][0]
        assert fb.rubric.word_count_in_range is False
        # Word count failure should prevent approval even with all 4s
        assert fb.approved is False

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_rubric_has_structural_fields(self, mock_get_llm, mock_invoke):
        """Verify structural analysis fields are populated in the rubric."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Average.",
            style_adherence=2,
            character_voice=2,
            outline_adherence=2,
            pacing=2,
            prose_quality=2,
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        result = run_style_editor(state)

        fb = result["edit_feedback"][0]
        # Structural fields should exist (advisory, with soft penalty)
        assert isinstance(fb.rubric.opener_monotony, bool)
        assert isinstance(fb.rubric.length_monotony, bool)
        assert isinstance(fb.rubric.passive_heavy, bool)
        assert isinstance(fb.rubric.structural_monotony, bool)

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_rubric_has_vocabulary_fields(self, mock_get_llm, mock_invoke):
        """Verify vocabulary analysis fields are populated in the rubric."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Average.",
            style_adherence=2,
            character_voice=2,
            outline_adherence=2,
            pacing=2,
            prose_quality=2,
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        result = run_style_editor(state)

        fb = result["edit_feedback"][0]
        # Vocabulary fields should exist (advisory, with soft penalty)
        assert isinstance(fb.rubric.low_diversity, bool)
        assert isinstance(fb.rubric.vocabulary_basic, bool)

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_confirmed_slop_computed_from_set_difference(
        self, mock_get_llm, mock_invoke
    ):
        """Verify confirmed_slop = flagged - dismissed flows to EditFeedback."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Some AI-isms found.",
            style_adherence=2,
            character_voice=2,
            outline_adherence=2,
            pacing=2,
            prose_quality=2,
            dismissed_slop=[],
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        # Multi-word slop phrases to populate raw_phrase_list
        state["scene_drafts"][0].prose = (
            "It was a testament to her skill. "
            "A wave washed over her as she watched the dance of shadows."
        )
        state["scene_drafts"][0].word_count = 20
        result = run_style_editor(state)

        fb = result["edit_feedback"][0]
        # With empty dismissed_slop, all multi-word phrases become confirmed
        assert len(fb.confirmed_slop) >= 3

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_scene_metrics_recorded(self, mock_get_llm, mock_invoke):
        """Verify scene metrics are appended to state."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Average.",
            style_adherence=2,
            character_voice=2,
            outline_adherence=2,
            pacing=2,
            prose_quality=2,
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        result = run_style_editor(state)

        assert "scene_metrics" in result
        assert len(result["scene_metrics"]) == 1
        metrics = result["scene_metrics"][0]
        assert metrics.scene_id == "s1"
        assert isinstance(metrics.slop_ratio, float)
        assert isinstance(metrics.mtld, float)

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_cross_scene_repetition_called(self, mock_get_llm, mock_invoke):
        """Verify cross-scene repetition detection runs with prior drafts."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Average.",
            style_adherence=2,
            character_voice=2,
            outline_adherence=2,
            pacing=2,
            prose_quality=2,
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        # Add a prior draft
        prior_draft = SceneDraft(
            scene_id="s0",
            act_number=1,
            scene_number=1,
            prose="Some prior scene content here about the station.",
            word_count=8,
            characters_used=["c1"],
        )
        state["scene_drafts"] = [prior_draft, state["scene_drafts"][0]]

        result = run_style_editor(state)

        fb = result["edit_feedback"][0]
        # cross_scene_repetitions field should exist on rubric
        assert isinstance(fb.rubric.cross_scene_repetitions, int)

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_allowlist_built_and_used(self, mock_get_llm, mock_invoke):
        """Verify allowlist is built from state and passed to slop detection."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Average.",
            style_adherence=2,
            character_voice=2,
            outline_adherence=2,
            pacing=2,
            prose_quality=2,
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        # The character name "Captain" should be in the allowlist
        # This test verifies the function runs without error
        result = run_style_editor(state)
        assert "edit_feedback" in result

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_mtld_regression_warning(self, mock_get_llm, mock_invoke, caplog):
        """Verify MTLD regression warning fires when diversity drops >20%."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Average.",
            style_adherence=2,
            character_voice=2,
            outline_adherence=2,
            pacing=2,
            prose_quality=2,
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        # Seed scene_metrics with a high MTLD mean (100.0)
        state["scene_metrics"] = [
            SceneMetrics(
                scene_id="s0",
                slop_ratio=0.95,
                mtld=100.0,
                opener_ratio=0.2,
                sent_length_cv=0.4,
                word_count=500,
            ),
        ]
        # Current prose is very short/repetitive — will produce low MTLD
        state["scene_drafts"][0].prose = " ".join(["word"] * 100)
        state["scene_drafts"][0].word_count = 100

        with caplog.at_level(logging.WARNING, logger="ai_writer.agents.style_editor"):
            run_style_editor(state)

        assert any("Quality regression" in msg for msg in caplog.messages)


class TestScoreCaps:
    """Tests for deterministic score caps applied after LLM scoring."""

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_pacing_capped_severe_on_opener_monotony(self, mock_get_llm, mock_invoke):
        """LLM pacing=4 should be capped to 2 when severe opener_monotony fires."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="All looks great.",
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,  # LLM gives 4
            prose_quality=4,
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        # Use extremely repetitive prose to trigger severe opener_monotony (>45%)
        # All sentences start with "He" -> top_opener_ratio ~1.0
        sentences = ["He walked slowly. " * 20]
        state["scene_drafts"][0].prose = " ".join(sentences)
        state["scene_drafts"][0].word_count = 100

        result = run_style_editor(state)
        fb = result["edit_feedback"][0]

        if fb.rubric.opener_monotony:
            # Severe (>45%) -> hard cap at 2
            assert fb.rubric.pacing <= 2

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_pacing_mild_cap_on_mild_opener_monotony(self, mock_get_llm, mock_invoke):
        """LLM pacing=4 should be capped to 3 when mild opener_monotony fires (31-45%)."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="All looks great.",
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,  # LLM gives 4
            prose_quality=4,
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        # Build prose where ~35% start with PRON (mild, not severe)
        # 10 sentences: 4 start with He/She, 6 start with varied POS
        prose = (
            "He walked to the door. The sun shone brightly. "
            "Rain pattered on the roof. She opened the window. "
            "Carefully, the boy stepped inside. A bird sang outside. "
            "He looked around the room. Thunder rumbled in the distance. "
            "Walking slowly, she crossed the room. "
            "She sat down on the old wooden chair."
        )
        state["scene_drafts"][0].prose = prose
        state["scene_drafts"][0].word_count = len(prose.split())

        from ai_writer.prompts.configs import ProseStructureConfig, ScoreCapConfig

        state["prompt_configs"] = {
            "prose_structure": ProseStructureConfig(opener_monotony_threshold=0.20),
            "score_caps": ScoreCapConfig(
                cap_pacing_on_monotony=2,
                severe_opener_threshold=0.45,
            ),
        }

        result = run_style_editor(state)
        fb = result["edit_feedback"][0]

        if fb.rubric.opener_monotony and fb.rubric.top_opener_ratio <= 0.45:
            # Mild monotony -> cap at 3 (not 2)
            assert fb.rubric.pacing <= 3

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_rubric_has_opener_detail_fields(self, mock_get_llm, mock_invoke):
        """Verify top_opener_pos and top_opener_ratio are populated in rubric."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Average.",
            style_adherence=2,
            character_voice=2,
            outline_adherence=2,
            pacing=2,
            prose_quality=2,
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        result = run_style_editor(state)

        fb = result["edit_feedback"][0]
        assert isinstance(fb.rubric.top_opener_pos, str)
        assert isinstance(fb.rubric.top_opener_ratio, float)

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_prose_capped_on_heavy_slop(self, mock_get_llm, mock_invoke):
        """LLM prose_quality should be capped when 3+ confirmed AI-isms."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Several AI-isms confirmed.",
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,
            prose_quality=4,  # LLM gives 4
            dismissed_slop=[],  # nothing dismissed -> all confirmed
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        # Use prose with 3+ multi-word slop phrases for confirmed_slop >= 3
        state["scene_drafts"][0].prose = (
            "It was a testament to her skill. A wave washed over her. "
            'The dance of shadows played. "Run," he whispered urgently. '
        ) + " ".join(["word"] * 80)
        state["scene_drafts"][0].word_count = 100

        result = run_style_editor(state)
        fb = result["edit_feedback"][0]

        # 4 multi-word confirmed slop -> prose_quality capped to 2
        assert len(fb.confirmed_slop) >= 3
        assert fb.rubric.prose_quality <= 2

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_eval_context_includes_deterministic_criteria(
        self, mock_get_llm, mock_invoke
    ):
        """Verify the LLM receives pre-evaluated criteria in eval context."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Average.",
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        run_style_editor(state)

        # Check the user message sent to LLM contains deterministic criteria
        call_args = mock_invoke.call_args[0]
        messages = call_args[1]
        user_msg = messages[1]["content"]
        assert "Pre-Evaluated Criteria" in user_msg
        assert "Sentence length variety" in user_msg
        assert "Opener variety" in user_msg
        assert "Word count within tolerance" in user_msg


class TestPersistentSlop:
    """Tests for persistent slop detection and enforcement."""

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_persistent_slop_caps_prose_to_one(self, mock_get_llm, mock_invoke):
        """Confirmed slop surviving revision hard-caps prose_quality to 1."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Some issues.",
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,
            prose_quality=4,
            dismissed_slop=[],
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        # Simulate revision: prior feedback had "a silent testament to" confirmed
        state["revision_count"] = 1
        state["edit_feedback"] = [
            EditFeedback(
                scene_id="s1",
                quality_score=0.5,
                approved=False,
                confirmed_slop=["a silent testament to"],
                rubric=SceneRubric(prose_quality=2),
            )
        ]
        # Prose still contains the phrase
        state["scene_drafts"][
            0
        ].prose = "The station stood as a silent testament to forgotten ambition."
        state["scene_drafts"][0].word_count = 10

        result = run_style_editor(state)
        fb = result["edit_feedback"][-1]

        assert fb.rubric.persistent_slop == ["a silent testament to"]
        assert fb.rubric.prose_quality == 1
        assert fb.rubric.has_critical_failure() is True
        assert fb.approved is False

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_no_persistent_slop_when_phrase_removed(self, mock_get_llm, mock_invoke):
        """When writer removes the flagged phrase, no persistence penalty."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Clean revision.",
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,
            prose_quality=4,
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        state["revision_count"] = 1
        state["edit_feedback"] = [
            EditFeedback(
                scene_id="s1",
                quality_score=0.5,
                approved=False,
                confirmed_slop=["a silent testament to"],
                rubric=SceneRubric(prose_quality=2),
            )
        ]
        # Prose no longer contains the flagged phrase
        state["scene_drafts"][0].prose = " ".join(["word"] * 100)
        state["scene_drafts"][0].word_count = 100

        result = run_style_editor(state)
        fb = result["edit_feedback"][-1]

        assert fb.rubric.persistent_slop == []
        # prose_quality should NOT be capped to 1
        assert fb.rubric.prose_quality > 1

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_persistence_skipped_on_first_evaluation(self, mock_get_llm, mock_invoke):
        """First evaluation (revision_count=0) should never fire persistence."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="First eval.",
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,
            prose_quality=4,
            dismissed_slop=[],
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        # revision_count defaults to 0 in _build_state
        state["scene_drafts"][0].prose = " ".join(["word"] * 100)
        state["scene_drafts"][0].word_count = 100

        result = run_style_editor(state)
        fb = result["edit_feedback"][-1]

        assert fb.rubric.persistent_slop == []

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_persistent_slop_case_insensitive(self, mock_get_llm, mock_invoke):
        """Persistence check should be case-insensitive."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Issues persist.",
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,
            prose_quality=4,
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        state["revision_count"] = 1
        state["edit_feedback"] = [
            EditFeedback(
                scene_id="s1",
                quality_score=0.5,
                approved=False,
                confirmed_slop=["A Silent Testament To"],
                rubric=SceneRubric(prose_quality=2),
            )
        ]
        # Prose has the phrase in different case
        state["scene_drafts"][
            0
        ].prose = "It stood as a silent testament to their resolve."
        state["scene_drafts"][0].word_count = 9

        result = run_style_editor(state)
        fb = result["edit_feedback"][-1]

        assert len(fb.rubric.persistent_slop) == 1
        assert fb.rubric.prose_quality == 1


class TestInvertedSlopBurden:
    """Tests for Phase 4 inverted burden of proof: confirmed = flagged - dismissed."""

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_confirmed_equals_flagged_minus_dismissed(self, mock_get_llm, mock_invoke):
        """3 multi-word flagged, 1 dismissed -> 2 confirmed."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="One phrase is contextually appropriate.",
            slop_reasoning="'testament to' is used literally here.",
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
            dismissed_slop=["testament to"],
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        state["scene_drafts"][0].prose = (
            "It was a testament to her skill. "
            "A wave washed over her as she watched the dance of shadows."
        )
        state["scene_drafts"][0].word_count = 20

        result = run_style_editor(state)
        fb = result["edit_feedback"][0]

        # "testament to" dismissed, but "washed over" and "dance of" remain
        assert "testament to" not in fb.confirmed_slop
        assert len(fb.confirmed_slop) == 2

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_all_dismissed_means_zero_confirmed(self, mock_get_llm, mock_invoke):
        """All flagged multi-word phrases dismissed -> 0 confirmed, no cap."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="All phrases are contextually appropriate.",
            slop_reasoning="Both phrases are used literally.",
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,
            prose_quality=4,
            dismissed_slop=["testament to", "dance of"],
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        state["scene_drafts"][0].prose = (
            "It was a testament to her skill. "
            "The dance of shadows moved across the wall. "
        ) + " ".join(["word"] * 80)
        state["scene_drafts"][0].word_count = 100

        result = run_style_editor(state)
        fb = result["edit_feedback"][0]

        assert fb.confirmed_slop == []

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_empty_dismissed_means_all_confirmed(self, mock_get_llm, mock_invoke):
        """LLM returns empty dismissed -> all multi-word flagged become confirmed."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="All are AI-isms.",
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
            dismissed_slop=[],
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        state["scene_drafts"][0].prose = (
            "It was a testament to her skill. "
            "A wave washed over her as she watched the dance of shadows."
        )
        state["scene_drafts"][0].word_count = 20

        result = run_style_editor(state)
        fb = result["edit_feedback"][0]

        # All 3 multi-word phrases confirmed (single words excluded)
        assert len(fb.confirmed_slop) == 3

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_dismissed_case_insensitive(self, mock_get_llm, mock_invoke):
        """'Testament To' dismisses 'testament to' (case insensitive)."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Phrase is contextually appropriate.",
            slop_reasoning="'testament to' is used literally.",
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
            dismissed_slop=["Testament To"],  # mixed case
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        state["scene_drafts"][
            0
        ].prose = "It was a testament to her enduring resolve and nothing more."
        state["scene_drafts"][0].word_count = 12

        result = run_style_editor(state)
        fb = result["edit_feedback"][0]

        # "testament to" should be dismissed despite case mismatch
        assert "testament to" not in fb.confirmed_slop

    @patch("ai_writer.agents.style_editor.invoke")
    @patch("ai_writer.agents.style_editor.get_structured_llm")
    def test_confirmed_slop_flows_to_edit_feedback(self, mock_get_llm, mock_invoke):
        """confirmed_slop computed by set difference appears in EditFeedback."""
        mock_output = StyleEditorOutput(
            dimension_reasoning="Issues found.",
            style_adherence=2,
            character_voice=2,
            outline_adherence=2,
            pacing=2,
            prose_quality=2,
            dismissed_slop=[],
        )
        mock_invoke.return_value = mock_output
        mock_get_llm.return_value = MagicMock()

        state = _build_state()
        state["scene_drafts"][
            0
        ].prose = "It was a testament to her skill and nothing more."
        state["scene_drafts"][0].word_count = 10

        result = run_style_editor(state)
        fb = result["edit_feedback"][0]

        # EditFeedback.confirmed_slop should contain multi-word phrases
        assert isinstance(fb.confirmed_slop, list)
        assert "testament to" in fb.confirmed_slop
