"""Tests for Beat Outliner agent."""

from unittest.mock import MagicMock, patch

from ai_writer.agents.beat_outliner import run_beat_outliner
from ai_writer.schemas.characters import (
    CharacterProfile,
    CharacterRole,
    CharacterRoster,
)
from ai_writer.schemas.story import Genre, StoryBrief
from ai_writer.schemas.structure import (
    ActOutline,
    BeatType,
    NarrativeBeat,
    SceneOutline,
    StoryOutline,
)
from ai_writer.schemas.world import WorldContext


def _mock_outline():
    return StoryOutline(
        acts=[
            ActOutline(
                act_number=1,
                title="Act One",
                beats=[
                    NarrativeBeat(
                        beat_id="b1",
                        act_number=1,
                        sequence_number=1,
                        beat_type=BeatType.HOOK,
                        summary="Opening",
                    ),
                ],
                scenes=[
                    SceneOutline(scene_id="s1", act_number=1, scene_number=1),
                    SceneOutline(scene_id="s2", act_number=1, scene_number=2),
                ],
            )
        ]
    )


class TestBeatOutliner:
    @patch("ai_writer.agents.beat_outliner.get_structured_llm")
    @patch("ai_writer.agents.beat_outliner.get_settings")
    def test_returns_story_outline(self, mock_settings, mock_get_llm):
        mock_settings.return_value = MagicMock(planning_temperature=0.3)

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_outline()
        mock_get_llm.return_value = mock_llm

        state = {
            "story_brief": StoryBrief(
                title="Test",
                premise="A story",
                genre=Genre.SCI_FI,
                themes=["hope"],
            ),
            "character_roster": CharacterRoster(
                characters=[
                    CharacterProfile(
                        character_id="c1",
                        name="Hero",
                        role=CharacterRole.PROTAGONIST,
                    )
                ]
            ),
            "world_context": WorldContext(setting_period="future"),
        }
        result = run_beat_outliner(state)

        assert "story_outline" in result
        assert result["current_stage"] == "writing"
        assert result["story_outline"].total_scenes == 2
