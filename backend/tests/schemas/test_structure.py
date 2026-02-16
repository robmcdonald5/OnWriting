"""Tests for structural decomposition schemas."""

import pytest
from pydantic import ValidationError

from ai_writer.schemas.structure import (
    ActOutline,
    BeatType,
    EmotionalValence,
    NarrativeBeat,
    SceneOutline,
    StoryOutline,
)


class TestNarrativeBeat:
    def test_valid_construction(self):
        beat = NarrativeBeat(
            beat_id="b1",
            act_number=1,
            sequence_number=1,
            beat_type=BeatType.HOOK,
            summary="The story opens with a mystery",
        )
        assert beat.beat_type == BeatType.HOOK
        assert beat.emotional_valence == EmotionalValence.NEUTRAL

    def test_act_number_constraint(self):
        with pytest.raises(ValidationError):
            NarrativeBeat(
                beat_id="b1",
                act_number=0,
                sequence_number=1,
                beat_type=BeatType.HOOK,
                summary="test",
            )


class TestSceneOutline:
    def test_valid_construction(self):
        scene = SceneOutline(
            scene_id="s1",
            act_number=1,
            scene_number=1,
            title="Opening",
            characters_present=["c1", "c2"],
            scene_goal="Establish the world",
        )
        assert scene.target_word_count == 1000
        assert len(scene.characters_present) == 2

    def test_target_word_count_constraint(self):
        with pytest.raises(ValidationError):
            SceneOutline(
                scene_id="s1", act_number=1, scene_number=1, target_word_count=0
            )


class TestStoryOutline:
    def test_computed_properties(self):
        outline = StoryOutline(
            acts=[
                ActOutline(
                    act_number=1,
                    beats=[
                        NarrativeBeat(
                            beat_id="b1",
                            act_number=1,
                            sequence_number=1,
                            beat_type=BeatType.HOOK,
                            summary="hook",
                        ),
                        NarrativeBeat(
                            beat_id="b2",
                            act_number=1,
                            sequence_number=2,
                            beat_type=BeatType.CLIMAX,
                            summary="climax",
                        ),
                    ],
                    scenes=[
                        SceneOutline(scene_id="s1", act_number=1, scene_number=1),
                        SceneOutline(scene_id="s2", act_number=1, scene_number=2),
                        SceneOutline(scene_id="s3", act_number=1, scene_number=3),
                    ],
                ),
            ]
        )
        assert outline.total_beats == 2
        assert outline.total_scenes == 3

    def test_empty_outline(self):
        outline = StoryOutline()
        assert outline.total_beats == 0
        assert outline.total_scenes == 0
