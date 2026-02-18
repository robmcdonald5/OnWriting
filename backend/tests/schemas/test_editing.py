"""Tests for editor feedback schemas."""

import pytest
from pydantic import ValidationError

from ai_writer.schemas.editing import (
    DIMENSION_WEIGHTS,
    EditFeedback,
    EditItem,
    EditSeverity,
    EditType,
    SceneRubric,
    StyleEditorOutput,
)


class TestEditItem:
    def test_valid_construction(self):
        item = EditItem(
            edit_type=EditType.STYLE,
            severity=EditSeverity.SUGGESTION,
            rationale="Smoother flow",
        )
        assert item.edit_type == EditType.STYLE
        assert item.original_text == ""


class TestStyleEditorOutput:
    def test_valid_construction(self):
        output = StyleEditorOutput(
            style_adherence=2,
            character_voice=3,
            outline_adherence=2,
            pacing=2,
            prose_quality=1,
            dimension_reasoning="Evidence here.",
        )
        assert output.style_adherence == 2
        assert output.prose_quality == 1

    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            StyleEditorOutput(
                style_adherence=0,  # below min
                character_voice=2,
                outline_adherence=2,
                pacing=2,
                prose_quality=2,
                dimension_reasoning="x",
            )
        with pytest.raises(ValidationError):
            StyleEditorOutput(
                style_adherence=4,  # above max
                character_voice=2,
                outline_adherence=2,
                pacing=2,
                prose_quality=2,
                dimension_reasoning="x",
            )


class TestSceneRubric:
    def _make_rubric(self, **overrides):
        defaults = dict(
            word_count_in_range=True,
            tense_consistent=True,
            slop_ratio=1.0,
            style_adherence=2,
            character_voice=2,
            outline_adherence=2,
            pacing=2,
            prose_quality=2,
        )
        defaults.update(overrides)
        return SceneRubric(**defaults)

    def test_compute_quality_score_all_twos(self):
        rubric = self._make_rubric()
        score = rubric.compute_quality_score()
        # All 2s: weighted_sum = 2.0, normalized = (2.0 - 1.0) / 2.0 = 0.5
        assert score == 0.5

    def test_compute_quality_score_all_threes(self):
        rubric = self._make_rubric(
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
        )
        score = rubric.compute_quality_score()
        # All 3s: weighted_sum = 3.0, normalized = (3.0 - 1.0) / 2.0 = 1.0
        assert score == 1.0

    def test_compute_quality_score_all_ones(self):
        rubric = self._make_rubric(
            style_adherence=1,
            character_voice=1,
            outline_adherence=1,
            pacing=1,
            prose_quality=1,
        )
        score = rubric.compute_quality_score()
        # All 1s: weighted_sum = 1.0, normalized = 0.0
        assert score == 0.0

    def test_compute_quality_score_mixed(self):
        rubric = self._make_rubric(
            style_adherence=3,  # weight 0.25
            character_voice=2,  # weight 0.20
            outline_adherence=3,  # weight 0.25
            pacing=2,  # weight 0.15
            prose_quality=2,  # weight 0.15
        )
        score = rubric.compute_quality_score()
        # weighted_sum = 3*0.25 + 2*0.20 + 3*0.25 + 2*0.15 + 2*0.15
        # = 0.75 + 0.40 + 0.75 + 0.30 + 0.30 = 2.50
        # normalized = (2.50 - 1.0) / 2.0 = 0.75
        assert score == 0.75

    def test_compute_quality_score_high_mix(self):
        rubric = self._make_rubric(
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=2,
            prose_quality=2,
        )
        score = rubric.compute_quality_score()
        # weighted_sum = 3*0.25 + 3*0.20 + 3*0.25 + 2*0.15 + 2*0.15
        # = 0.75 + 0.60 + 0.75 + 0.30 + 0.30 = 2.70
        # normalized = (2.70 - 1.0) / 2.0 = 0.85
        assert score == 0.85

    def test_has_critical_failure_true(self):
        rubric = self._make_rubric(character_voice=1)
        assert rubric.has_critical_failure() is True

    def test_has_critical_failure_false(self):
        rubric = self._make_rubric()
        assert rubric.has_critical_failure() is False

    def test_compute_approved_passes(self):
        rubric = self._make_rubric(
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=2,
            prose_quality=2,
        )
        # Score = 0.75, no critical failure, deterministic OK
        assert rubric.compute_approved() is True

    def test_compute_approved_fails_on_low_score(self):
        rubric = self._make_rubric()
        # Score = 0.5, below 0.7 threshold
        assert rubric.compute_approved() is False

    def test_compute_approved_fails_on_critical_failure(self):
        rubric = self._make_rubric(
            style_adherence=3,
            character_voice=1,  # critical
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
        )
        # Score is high but has critical failure
        assert rubric.compute_approved() is False

    def test_compute_approved_fails_on_deterministic(self):
        rubric = self._make_rubric(
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
            word_count_in_range=False,  # deterministic fail
        )
        assert rubric.compute_approved() is False

    def test_slop_ratio_does_not_block_approval(self):
        """Slop is advisory only — fed to LLM context, not a hard gate."""
        rubric = self._make_rubric(
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
            slop_ratio=0.3,
        )
        assert rubric.compute_approved() is True

    def test_dimension_summary(self):
        rubric = self._make_rubric()
        summary = rubric.dimension_summary()
        assert "style=2/3" in summary
        assert "voice=2/3" in summary
        assert "outline=2/3" in summary
        assert "pacing=2/3" in summary
        assert "prose=2/3" in summary

    def test_weight_keys_match_rubric_dimensions(self):
        """DIMENSION_WEIGHTS must cover exactly the scored dimensions."""
        expected = {
            "style_adherence",
            "character_voice",
            "outline_adherence",
            "pacing",
            "prose_quality",
        }
        assert set(DIMENSION_WEIGHTS.keys()) == expected

    def test_weights_sum_to_one(self):
        """Weights must sum to 1.0 for correct normalization."""
        assert abs(sum(DIMENSION_WEIGHTS.values()) - 1.0) < 1e-9


class TestEditFeedback:
    def test_valid_construction(self):
        fb = EditFeedback(
            scene_id="s1",
            quality_score=0.85,
            approved=True,
            overall_assessment="Good scene.",
        )
        assert fb.approved is True
        assert fb.quality_score == 0.85

    def test_quality_score_bounds(self):
        with pytest.raises(ValidationError):
            EditFeedback(scene_id="s1", quality_score=1.5)
        with pytest.raises(ValidationError):
            EditFeedback(scene_id="s1", quality_score=-0.1)

    def test_default_not_approved(self):
        fb = EditFeedback(scene_id="s1")
        assert fb.approved is False
        assert fb.quality_score == 0.0

    def test_rubric_defaults(self):
        fb = EditFeedback(scene_id="s1")
        assert fb.rubric is not None
        assert fb.rubric.word_count_in_range is True
        assert fb.rubric.style_adherence == 2

    def test_with_rubric(self):
        rubric = SceneRubric(
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=2,
            prose_quality=2,
        )
        fb = EditFeedback(
            scene_id="s1",
            quality_score=rubric.compute_quality_score(),
            approved=rubric.compute_approved(),
            rubric=rubric,
        )
        # style=3*0.25 + voice=3*0.20 + outline=3*0.25 + pacing=2*0.15 + prose=2*0.15
        # = 0.75 + 0.60 + 0.75 + 0.30 + 0.30 = 2.70 → (2.70-1)/2 = 0.85
        assert fb.quality_score == 0.85
        assert fb.approved is True
