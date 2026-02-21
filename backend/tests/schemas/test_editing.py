"""Tests for editor feedback schemas."""

import pytest
from pydantic import ValidationError

from ai_writer.schemas.editing import (
    DIMENSION_WEIGHTS,
    EditFeedback,
    EditItem,
    EditSeverity,
    EditType,
    SceneMetrics,
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
            dimension_reasoning="Evidence here.",
            style_adherence=2,
            character_voice=3,
            outline_adherence=2,
            pacing=2,
            prose_quality=1,
        )
        assert output.style_adherence == 2
        assert output.prose_quality == 1

    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            StyleEditorOutput(
                dimension_reasoning="x",
                style_adherence=0,  # below min
                character_voice=2,
                outline_adherence=2,
                pacing=2,
                prose_quality=2,
            )
        with pytest.raises(ValidationError):
            StyleEditorOutput(
                dimension_reasoning="x",
                style_adherence=5,  # above max (now 4 is max)
                character_voice=2,
                outline_adherence=2,
                pacing=2,
                prose_quality=2,
            )

    def test_score_4_is_valid(self):
        """Score 4 is now the maximum on the expanded scale."""
        output = StyleEditorOutput(
            dimension_reasoning="Excellent.",
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,
            prose_quality=4,
        )
        assert output.style_adherence == 4

    def test_confirmed_slop_field(self):
        output = StyleEditorOutput(
            dimension_reasoning="Evidence.",
            style_adherence=2,
            character_voice=2,
            outline_adherence=2,
            pacing=2,
            prose_quality=2,
            confirmed_slop=["testament to", "tapestry of"],
        )
        assert output.confirmed_slop == ["testament to", "tapestry of"]

    def test_confirmed_slop_defaults_empty(self):
        output = StyleEditorOutput(
            dimension_reasoning="Evidence.",
            style_adherence=2,
            character_voice=2,
            outline_adherence=2,
            pacing=2,
            prose_quality=2,
        )
        assert output.confirmed_slop == []

    def test_reasoning_first_field(self):
        """dimension_reasoning should be the first field for critique-before-score."""
        fields = list(StyleEditorOutput.model_fields.keys())
        assert fields[0] == "dimension_reasoning"


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
        # All 2s: weighted_sum = 2.0, normalized = (2.0 - 1.0) / 3.0 = 0.33
        assert score == 0.33

    def test_compute_quality_score_all_fours(self):
        rubric = self._make_rubric(
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,
            prose_quality=4,
        )
        score = rubric.compute_quality_score()
        # All 4s: weighted_sum = 4.0, normalized = (4.0 - 1.0) / 3.0 = 1.0
        assert score == 1.0

    def test_compute_quality_score_all_threes(self):
        rubric = self._make_rubric(
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
        )
        score = rubric.compute_quality_score()
        # All 3s: weighted_sum = 3.0, normalized = (3.0 - 1.0) / 3.0 = 0.67
        assert score == 0.67

    def test_all_threes_below_threshold(self):
        """All-3s should NOT auto-pass (below 0.7 threshold)."""
        rubric = self._make_rubric(
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
        )
        assert rubric.compute_approved() is False

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

    def test_compute_quality_score_mixed_3s_and_4s(self):
        rubric = self._make_rubric(
            style_adherence=4,  # weight 0.20
            character_voice=3,  # weight 0.20
            outline_adherence=4,  # weight 0.20
            pacing=3,  # weight 0.20
            prose_quality=3,  # weight 0.20
        )
        score = rubric.compute_quality_score()
        # weighted_sum = 4*0.20 + 3*0.20 + 4*0.20 + 3*0.20 + 3*0.20
        # = 0.80 + 0.60 + 0.80 + 0.60 + 0.60 = 3.40
        # normalized = (3.40 - 1.0) / 3.0 = 0.80
        assert score == 0.8

    def test_compute_quality_score_high_mix(self):
        rubric = self._make_rubric(
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=3,
            prose_quality=3,
        )
        score = rubric.compute_quality_score()
        # weighted_sum = 4*0.20 + 4*0.20 + 4*0.20 + 3*0.20 + 3*0.20
        # = 0.80 + 0.80 + 0.80 + 0.60 + 0.60 = 3.60
        # normalized = (3.60 - 1.0) / 3.0 = 0.867 -> 0.87
        assert score == 0.87

    def test_has_critical_failure_true(self):
        rubric = self._make_rubric(character_voice=1)
        assert rubric.has_critical_failure() is True

    def test_has_critical_failure_false(self):
        rubric = self._make_rubric()
        assert rubric.has_critical_failure() is False

    def test_compute_approved_passes(self):
        rubric = self._make_rubric(
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=3,
            prose_quality=3,
        )
        # Score = 0.90, no critical failure, deterministic OK
        assert rubric.compute_approved() is True

    def test_compute_approved_fails_on_low_score(self):
        rubric = self._make_rubric()
        # Score = 0.33, below 0.7 threshold
        assert rubric.compute_approved() is False

    def test_compute_approved_fails_on_critical_failure(self):
        rubric = self._make_rubric(
            style_adherence=4,
            character_voice=1,  # critical
            outline_adherence=4,
            pacing=4,
            prose_quality=4,
        )
        # Score is high but has critical failure
        assert rubric.compute_approved() is False

    def test_compute_approved_fails_on_deterministic(self):
        rubric = self._make_rubric(
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,
            prose_quality=4,
            word_count_in_range=False,  # deterministic fail
        )
        assert rubric.compute_approved() is False

    def test_slop_ratio_does_not_block_approval(self):
        """Slop is advisory only — fed to LLM context, not a hard gate."""
        rubric = self._make_rubric(
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,
            prose_quality=4,
            slop_ratio=0.3,
        )
        assert rubric.compute_approved() is True

    def test_dimension_summary(self):
        rubric = self._make_rubric()
        summary = rubric.dimension_summary()
        assert "style=2/4" in summary
        assert "voice=2/4" in summary
        assert "outline=2/4" in summary
        assert "pacing=2/4" in summary
        assert "prose=2/4" in summary

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


class TestSoftPenalty:
    def _make_rubric(self, **overrides):
        defaults = dict(
            word_count_in_range=True,
            tense_consistent=True,
            slop_ratio=1.0,
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,
            prose_quality=4,
        )
        defaults.update(overrides)
        return SceneRubric(**defaults)

    def test_soft_penalty_reduces_score(self):
        """Advisory flags should reduce the quality score."""
        clean = self._make_rubric()
        flagged = self._make_rubric(opener_monotony=True, low_diversity=True)
        assert flagged.compute_quality_score() < clean.compute_quality_score()

    def test_max_advisory_penalty_is_0_18(self):
        """All advisory flags together should produce max 0.18 penalty."""
        clean = self._make_rubric()
        all_flags = self._make_rubric(
            opener_monotony=True,
            length_monotony=True,
            passive_heavy=True,
            structural_monotony=True,
            low_diversity=True,
            vocabulary_basic=True,
        )
        clean_score = clean.compute_quality_score()
        flagged_score = all_flags.compute_quality_score()
        penalty = clean_score - flagged_score
        assert abs(penalty - 0.18) < 0.001

    def test_cross_scene_penalty_capped_at_0_06(self):
        """Cross-scene repetitions penalty maxes at 0.06 (3 * 0.02)."""
        clean = self._make_rubric()
        with_reps = self._make_rubric(cross_scene_repetitions=5)
        clean_score = clean.compute_quality_score()
        reps_score = with_reps.compute_quality_score()
        penalty = clean_score - reps_score
        assert abs(penalty - 0.06) < 0.001

    def test_borderline_scene_with_penalties(self):
        """All-3s (0.67) with opener_monotony + low_diversity drops well below threshold."""
        rubric = SceneRubric(
            word_count_in_range=True,
            tense_consistent=True,
            slop_ratio=1.0,
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
            opener_monotony=True,
            low_diversity=True,
        )
        score = rubric.compute_quality_score()
        # Base: 0.67, penalty: 0.04 + 0.04 = 0.08 -> 0.59
        assert score == 0.59
        assert rubric.compute_approved() is False

    def test_no_penalty_when_no_flags(self):
        """Score should match pure dimension calculation when no flags set."""
        rubric = self._make_rubric()
        # All 4s -> normalized = 1.0, no penalty
        assert rubric.compute_quality_score() == 1.0


class TestCrossSceneRepetitions:
    def test_cross_scene_field_defaults_zero(self):
        rubric = SceneRubric()
        assert rubric.cross_scene_repetitions == 0

    def test_cross_scene_field_stored(self):
        rubric = SceneRubric(cross_scene_repetitions=3)
        assert rubric.cross_scene_repetitions == 3


class TestSceneMetrics:
    def test_serializes_correctly(self):
        metrics = SceneMetrics(
            scene_id="s1",
            slop_ratio=0.92,
            mtld=72.5,
            opener_ratio=0.35,
            sent_length_cv=0.42,
            word_count=1050,
        )
        data = metrics.model_dump()
        assert data["scene_id"] == "s1"
        assert data["slop_ratio"] == 0.92
        assert data["mtld"] == 72.5
        assert data["opener_ratio"] == 0.35
        assert data["sent_length_cv"] == 0.42
        assert data["word_count"] == 1050

    def test_roundtrips_json(self):
        metrics = SceneMetrics(
            scene_id="s2",
            slop_ratio=0.88,
            mtld=65.0,
            opener_ratio=0.28,
            sent_length_cv=0.55,
            word_count=900,
        )
        json_str = metrics.model_dump_json()
        restored = SceneMetrics.model_validate_json(json_str)
        assert restored == metrics


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

    def test_confirmed_slop_field(self):
        fb = EditFeedback(
            scene_id="s1",
            confirmed_slop=["testament to", "delve into"],
        )
        assert fb.confirmed_slop == ["testament to", "delve into"]

    def test_confirmed_slop_defaults_empty(self):
        fb = EditFeedback(scene_id="s1")
        assert fb.confirmed_slop == []

    def test_with_rubric(self):
        rubric = SceneRubric(
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=3,
            prose_quality=3,
        )
        fb = EditFeedback(
            scene_id="s1",
            quality_score=rubric.compute_quality_score(),
            approved=rubric.compute_approved(),
            rubric=rubric,
        )
        # style=4*0.20 + voice=4*0.20 + outline=4*0.20 + pacing=3*0.20 + prose=3*0.20
        # = 0.80 + 0.80 + 0.80 + 0.60 + 0.60 = 3.60 -> (3.60-1)/3 = 0.87
        assert fb.quality_score == 0.87
        assert fb.approved is True
