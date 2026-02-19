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
                    style_adherence=3,
                    character_voice=3,
                    outline_adherence=3,
                    pacing=2,
                    prose_quality=2,
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
                    style_adherence=3,
                    character_voice=3,
                    outline_adherence=3,
                    pacing=3,
                    prose_quality=3,
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

    def test_all_threes_approves(self):
        """All dimensions at 3 with clean deterministic checks → approve."""
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
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [fb],
            "revision_count": 0,
            "max_revisions": 2,
            "current_scene_index": 0,
            "story_outline": _one_scene_outline(),
        }
        assert should_revise_or_advance(state) == "complete"

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
        assert fb.quality_score == 0.5
        assert fb.approved is False
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
