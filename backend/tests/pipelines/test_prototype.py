"""Tests for the prototype pipeline."""

from ai_writer.pipelines.prototype import (
    GraphState,
    advance_scene,
    build_prototype_pipeline,
    mark_complete,
    prepare_revision,
    should_revise_or_advance,
)
from ai_writer.schemas.editing import EditFeedback
from ai_writer.schemas.structure import ActOutline, SceneOutline, StoryOutline


class TestConditionalEdges:
    def test_revise_when_not_approved_and_budget_remaining(self):
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [
                EditFeedback(scene_id="s1", quality_score=0.5, approved=False)
            ],
            "revision_count": 0,
            "max_revisions": 2,
            "current_scene_index": 0,
            "story_outline": StoryOutline(
                acts=[
                    ActOutline(
                        act_number=1,
                        scenes=[
                            SceneOutline(scene_id="s1", act_number=1, scene_number=1),
                        ],
                    )
                ]
            ),
        }
        assert should_revise_or_advance(state) == "revise"

    def test_advance_when_approved_and_more_scenes(self):
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [
                EditFeedback(scene_id="s1", quality_score=0.8, approved=True)
            ],
            "revision_count": 0,
            "max_revisions": 2,
            "current_scene_index": 0,
            "story_outline": StoryOutline(
                acts=[
                    ActOutline(
                        act_number=1,
                        scenes=[
                            SceneOutline(scene_id="s1", act_number=1, scene_number=1),
                            SceneOutline(scene_id="s2", act_number=1, scene_number=2),
                        ],
                    )
                ]
            ),
        }
        assert should_revise_or_advance(state) == "next_scene"

    def test_complete_when_approved_and_last_scene(self):
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [
                EditFeedback(scene_id="s1", quality_score=0.85, approved=True)
            ],
            "revision_count": 0,
            "max_revisions": 2,
            "current_scene_index": 0,
            "story_outline": StoryOutline(
                acts=[
                    ActOutline(
                        act_number=1,
                        scenes=[
                            SceneOutline(scene_id="s1", act_number=1, scene_number=1),
                        ],
                    )
                ]
            ),
        }
        assert should_revise_or_advance(state) == "complete"

    def test_advance_when_max_revisions_reached(self):
        state: GraphState = {
            "user_prompt": "test",
            "edit_feedback": [
                EditFeedback(scene_id="s1", quality_score=0.5, approved=False)
            ],
            "revision_count": 2,
            "max_revisions": 2,
            "current_scene_index": 0,
            "story_outline": StoryOutline(
                acts=[
                    ActOutline(
                        act_number=1,
                        scenes=[
                            SceneOutline(scene_id="s1", act_number=1, scene_number=1),
                            SceneOutline(scene_id="s2", act_number=1, scene_number=2),
                        ],
                    )
                ]
            ),
        }
        assert should_revise_or_advance(state) == "next_scene"


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
