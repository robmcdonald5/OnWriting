"""Tests for Plot Architect agent."""

from unittest.mock import MagicMock, patch

from ai_writer.agents.plot_architect import run_plot_architect
from ai_writer.schemas.characters import (
    CharacterProfile,
    CharacterRole,
    CharacterRoster,
)
from ai_writer.schemas.story import Genre, StoryBrief, ToneProfile
from ai_writer.schemas.world import Location, WorldContext


def _mock_story_brief():
    return StoryBrief(
        title="The Last Signal",
        premise="A lone astronaut receives a signal from a dead civilization",
        genre=Genre.SCI_FI,
        themes=["isolation", "hope"],
        tone_profile=ToneProfile(formality=0.6, darkness=0.7),
    )


def _mock_character_roster():
    return CharacterRoster(
        characters=[
            CharacterProfile(
                character_id="c1",
                name="Dr. Elara Voss",
                role=CharacterRole.PROTAGONIST,
                voice_notes="calm, scientific",
            ),
        ]
    )


def _mock_world_context():
    return WorldContext(
        setting_period="2347 AD",
        locations=[Location(location_id="loc1", name="Station Omega")],
    )


class TestPlotArchitect:
    @patch("ai_writer.agents.plot_architect.get_structured_llm")
    @patch("ai_writer.agents.plot_architect.get_settings")
    def test_returns_correct_keys(self, mock_settings, mock_get_llm):
        mock_settings.return_value = MagicMock(planning_temperature=0.3)

        mock_llm = MagicMock()
        # Three sequential calls: StoryBrief, CharacterRoster, WorldContext
        mock_llm.invoke.side_effect = [
            _mock_story_brief(),
            _mock_character_roster(),
            _mock_world_context(),
        ]
        mock_get_llm.return_value = mock_llm

        state = {"user_prompt": "Write a sci-fi story about isolation in space"}
        result = run_plot_architect(state)

        assert "story_brief" in result
        assert "character_roster" in result
        assert "world_context" in result
        assert result["current_stage"] == "outlining"

    @patch("ai_writer.agents.plot_architect.get_structured_llm")
    @patch("ai_writer.agents.plot_architect.get_settings")
    def test_makes_three_llm_calls(self, mock_settings, mock_get_llm):
        mock_settings.return_value = MagicMock(planning_temperature=0.3)

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            _mock_story_brief(),
            _mock_character_roster(),
            _mock_world_context(),
        ]
        mock_get_llm.return_value = mock_llm

        state = {"user_prompt": "A mystery story"}
        run_plot_architect(state)

        assert mock_get_llm.call_count == 3
        assert mock_llm.invoke.call_count == 3
