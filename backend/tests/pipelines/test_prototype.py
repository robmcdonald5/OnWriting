"""Tests for the prototype pipeline."""

from ai_writer.pipelines.prototype import (
    GraphState,
    advance_scene,
    build_prototype_pipeline,
    mark_complete,
    prepare_revision,
    should_revise_or_advance,
)
from ai_writer.schemas.editing import EditFeedback, SceneRubric
from ai_writer.schemas.structure import ActOutline, SceneOutline, StoryOutline


def _make_feedback(scene_id: str, approved: bool, **rubric_overrides) -> EditFeedback:
    """Build an EditFeedback with computed fields from rubric dimensions."""
    rubric = SceneRubric(**rubric_overrides)
    return EditFeedback(
        scene_id=scene_id,
        quality_score=rubric.compute_quality_score(),
        approved=approved,
        rubric=rubric,
    )


def _two_scene_outline() -> StoryOutline:
    return StoryOutline(
        acts=[
            ActOutline(
                act_number=1,
                scenes=[
                    SceneOutline(scene_id="s1", act_number=1, scene_number=1),
                    SceneOutline(scene_id="s2", act_number=1, scene_number=2),
                ],
            )
        ]
    )


def _one_scene_outline() -> StoryOutline:
    return StoryOutline(
        acts=[
            ActOutline(
                act_number=1,
                scenes=[
                    SceneOutline(scene_id="s1", act_number=1, scene_number=1),
                ],
            )
        ]
    )


class TestConditionalEdges:
    def test_revise_when_not_approved_and_budget_remaining(self):
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [
                _make_feedback("s1", approved=False, style_adherence=2, pacing=1)
            ],
            "revision_count": 0,
            "max_revisions": 2,
            "current_scene_index": 0,
            "story_outline": _one_scene_outline(),
        }
        assert should_revise_or_advance(state) == "revise"

    def test_advance_when_approved_and_more_scenes(self):
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [
                _make_feedback(
                    "s1",
                    approved=True,
                    style_adherence=4,
                    character_voice=4,
                    outline_adherence=4,
                    pacing=3,
                    prose_quality=3,
                )
            ],
            "revision_count": 0,
            "max_revisions": 2,
            "current_scene_index": 0,
            "story_outline": _two_scene_outline(),
        }
        assert should_revise_or_advance(state) == "next_scene"

    def test_complete_when_approved_and_last_scene(self):
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [
                _make_feedback(
                    "s1",
                    approved=True,
                    style_adherence=4,
                    character_voice=4,
                    outline_adherence=4,
                    pacing=4,
                    prose_quality=4,
                )
            ],
            "revision_count": 0,
            "max_revisions": 2,
            "current_scene_index": 0,
            "story_outline": _one_scene_outline(),
        }
        assert should_revise_or_advance(state) == "complete"

    def test_advance_when_max_revisions_reached(self):
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [
                _make_feedback("s1", approved=False, style_adherence=1, pacing=1)
            ],
            "revision_count": 2,
            "max_revisions": 2,
            "current_scene_index": 0,
            "story_outline": _two_scene_outline(),
        }
        assert should_revise_or_advance(state) == "next_scene"

    def test_all_fours_approves(self):
        """All dimensions at 4 with clean deterministic checks → approve."""
        rubric = SceneRubric(
            style_adherence=4,
            character_voice=4,
            outline_adherence=4,
            pacing=4,
            prose_quality=4,
        )
        fb = EditFeedback(
            scene_id="s1",
            quality_score=rubric.compute_quality_score(),
            approved=rubric.compute_approved(),
            rubric=rubric,
        )
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [fb],
            "revision_count": 0,
            "max_revisions": 2,
            "current_scene_index": 0,
            "story_outline": _one_scene_outline(),
        }
        assert should_revise_or_advance(state) == "complete"

    def test_all_threes_does_not_approve(self):
        """All-3s on 1-4 scale = 0.67, below 0.7 threshold → revision."""
        rubric = SceneRubric(
            style_adherence=3,
            character_voice=3,
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
        )
        fb = EditFeedback(
            scene_id="s1",
            quality_score=rubric.compute_quality_score(),
            approved=rubric.compute_approved(),
            rubric=rubric,
        )
        assert fb.quality_score == 0.67
        assert fb.approved is False

    def test_above_threshold_but_critical_failure_revises(self):
        """High average but one dimension at 1 → floor check triggers revision."""
        rubric = SceneRubric(
            style_adherence=3,
            character_voice=1,  # critical
            outline_adherence=3,
            pacing=3,
            prose_quality=3,
        )
        fb = EditFeedback(
            scene_id="s1",
            quality_score=rubric.compute_quality_score(),
            approved=rubric.compute_approved(),  # Should be False
            rubric=rubric,
        )
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [fb],
            "revision_count": 0,
            "max_revisions": 2,
            "current_scene_index": 0,
            "story_outline": _one_scene_outline(),
        }
        assert fb.approved is False
        assert should_revise_or_advance(state) == "revise"

    def test_below_threshold_revises(self):
        """Average below 0.7 → revision needed."""
        rubric = SceneRubric(
            style_adherence=2,
            character_voice=2,
            outline_adherence=2,
            pacing=2,
            prose_quality=2,
        )
        fb = EditFeedback(
            scene_id="s1",
            quality_score=rubric.compute_quality_score(),
            approved=rubric.compute_approved(),  # Should be False (0.5 < 0.7)
            rubric=rubric,
        )
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [fb],
            "revision_count": 0,
            "max_revisions": 2,
            "current_scene_index": 0,
            "story_outline": _one_scene_outline(),
        }
        assert fb.quality_score == 0.33
        assert fb.approved is False
        assert should_revise_or_advance(state) == "revise"


class TestMinRevisions:
    """Tests for the guaranteed minimum editing pass feature."""

    def test_force_revise_when_below_min_revisions(self):
        """Approved draft with revision_count=0, min=1 → force "revise"."""
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [
                _make_feedback(
                    "s1",
                    approved=True,
                    style_adherence=4,
                    character_voice=4,
                    outline_adherence=4,
                    pacing=4,
                    prose_quality=4,
                )
            ],
            "revision_count": 0,
            "max_revisions": 2,
            "min_revisions": 1,
            "current_scene_index": 0,
            "story_outline": _one_scene_outline(),
        }
        assert should_revise_or_advance(state) == "revise"

    def test_normal_logic_after_min_revisions_met(self):
        """Approved draft with revision_count=1, min=1 → "complete"."""
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [
                _make_feedback(
                    "s1",
                    approved=True,
                    style_adherence=4,
                    character_voice=4,
                    outline_adherence=4,
                    pacing=4,
                    prose_quality=4,
                )
            ],
            "revision_count": 1,
            "max_revisions": 2,
            "min_revisions": 1,
            "current_scene_index": 0,
            "story_outline": _one_scene_outline(),
        }
        assert should_revise_or_advance(state) == "complete"

    def test_min_revisions_zero_matches_old_behavior(self):
        """min=0, approved → "complete" (backward compat)."""
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [
                _make_feedback(
                    "s1",
                    approved=True,
                    style_adherence=4,
                    character_voice=4,
                    outline_adherence=4,
                    pacing=4,
                    prose_quality=4,
                )
            ],
            "revision_count": 0,
            "max_revisions": 2,
            "min_revisions": 0,
            "current_scene_index": 0,
            "story_outline": _one_scene_outline(),
        }
        assert should_revise_or_advance(state) == "complete"

    def test_min_revisions_default_is_zero_in_state(self):
        """min not set in state, approved → "complete" (backward compat)."""
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [
                _make_feedback(
                    "s1",
                    approved=True,
                    style_adherence=4,
                    character_voice=4,
                    outline_adherence=4,
                    pacing=4,
                    prose_quality=4,
                )
            ],
            "revision_count": 0,
            "max_revisions": 2,
            "current_scene_index": 0,
            "story_outline": _one_scene_outline(),
        }
        # min_revisions intentionally omitted — defaults to 0
        assert should_revise_or_advance(state) == "complete"

    def test_min_revisions_with_failing_score_still_revises(self):
        """Not approved + below min → "revise" (both reasons agree)."""
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [
                _make_feedback("s1", approved=False, style_adherence=2, pacing=1)
            ],
            "revision_count": 0,
            "max_revisions": 2,
            "min_revisions": 1,
            "current_scene_index": 0,
            "story_outline": _one_scene_outline(),
        }
        assert should_revise_or_advance(state) == "revise"

    def test_min_revisions_equals_max_revisions(self):
        """min=2, max=2: count=1 → "revise"; count=2 → "complete"."""
        base_state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [
                _make_feedback(
                    "s1",
                    approved=True,
                    style_adherence=4,
                    character_voice=4,
                    outline_adherence=4,
                    pacing=4,
                    prose_quality=4,
                )
            ],
            "max_revisions": 2,
            "min_revisions": 2,
            "current_scene_index": 0,
            "story_outline": _one_scene_outline(),
        }
        # count=1, still below min → revise
        state_1 = {**base_state, "revision_count": 1}
        assert should_revise_or_advance(state_1) == "revise"

        # count=2, min met and max reached → complete
        state_2 = {**base_state, "revision_count": 2}
        assert should_revise_or_advance(state_2) == "complete"

    def test_force_revise_next_scene_scenario(self):
        """Approved, 2 scenes, min=1, count=0 → "revise" (not "next_scene")."""
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [
                _make_feedback(
                    "s1",
                    approved=True,
                    style_adherence=4,
                    character_voice=4,
                    outline_adherence=4,
                    pacing=4,
                    prose_quality=4,
                )
            ],
            "revision_count": 0,
            "max_revisions": 2,
            "min_revisions": 1,
            "current_scene_index": 0,
            "story_outline": _two_scene_outline(),
        }
        assert should_revise_or_advance(state) == "revise"


class TestHelperNodes:
    def test_prepare_revision_increments(self):
        result = prepare_revision({"revision_count": 0})
        assert result["revision_count"] == 1

    def test_advance_scene_increments_and_resets(self):
        result = advance_scene({"current_scene_index": 0, "revision_count": 2})
        assert result["current_scene_index"] == 1
        assert result["revision_count"] == 0

    def test_mark_complete(self):
        result = mark_complete({})
        assert result["current_stage"] == "complete"


class TestPipelineCompilation:
    def test_pipeline_compiles(self):
        graph = build_prototype_pipeline()
        assert graph is not None
