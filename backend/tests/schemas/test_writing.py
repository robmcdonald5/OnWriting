"""Tests for writer output schemas."""

from ai_writer.schemas.writing import ActDraft, SceneDraft


class TestSceneDraft:
    def test_valid_construction(self):
        draft = SceneDraft(
            scene_id="s1",
            act_number=1,
            scene_number=1,
            prose="The station hummed quietly.",
            word_count=5,
        )
        assert draft.word_count == 5
        assert draft.notes_for_editor == ""


class TestActDraft:
    def test_computed_word_count(self):
        act = ActDraft(
            act_number=1,
            scenes=[
                SceneDraft(scene_id="s1", act_number=1, scene_number=1, word_count=500),
                SceneDraft(scene_id="s2", act_number=1, scene_number=2, word_count=750),
            ],
        )
        assert act.total_word_count == 1250

    def test_empty_act(self):
        act = ActDraft(act_number=1)
        assert act.total_word_count == 0
