"""Tests for story-aware allowlist extraction."""

from ai_writer.schemas.characters import (
    CharacterProfile,
    CharacterRole,
    CharacterRoster,
)
from ai_writer.schemas.story import Genre, StoryBrief
from ai_writer.schemas.world import Location, WorldContext
from ai_writer.utils.text_analysis import build_story_allowlist


class TestBuildStoryAllowlist:
    def test_extracts_character_names(self):
        state = {
            "character_roster": CharacterRoster(
                characters=[
                    CharacterProfile(
                        character_id="c1",
                        name="Elias Voss",
                        role=CharacterRole.PROTAGONIST,
                    ),
                ]
            ),
        }
        result = build_story_allowlist(state)
        assert "elias voss" in result
        assert "elias" in result
        assert "voss" in result

    def test_extracts_location_names(self):
        state = {
            "world_context": WorldContext(
                locations=[
                    Location(
                        location_id="loc1",
                        name="Meridian Station",
                    ),
                ]
            ),
        }
        result = build_story_allowlist(state)
        assert "meridian station" in result
        assert "meridian" in result
        assert "station" in result

    def test_extracts_theme_words(self):
        state = {
            "story_brief": StoryBrief(
                title="Test",
                premise="A story",
                genre=Genre.SCI_FI,
                themes=["isolation", "discovery"],
            ),
        }
        result = build_story_allowlist(state)
        assert "isolation" in result
        assert "discovery" in result

    def test_skips_short_words(self):
        """Words <= 3 chars from themes and <= 2 chars from names are skipped."""
        state = {
            "story_brief": StoryBrief(
                title="Test",
                premise="A story",
                genre=Genre.SCI_FI,
                themes=["war and ice"],
            ),
            "character_roster": CharacterRoster(
                characters=[
                    CharacterProfile(
                        character_id="c1",
                        name="Jo Li",
                        role=CharacterRole.PROTAGONIST,
                    ),
                ]
            ),
        }
        result = build_story_allowlist(state)
        # "war" and "and" and "ice" are <= 3 chars, excluded from themes
        assert "war" not in result
        assert "and" not in result
        assert "ice" not in result
        # "Jo" and "Li" are <= 2 chars, excluded from name parts
        assert "jo" not in result
        assert "li" not in result
        # But the full name is included
        assert "jo li" in result

    def test_empty_state_returns_empty_set(self):
        result = build_story_allowlist({})
        assert result == set()

    def test_missing_fields_handled_gracefully(self):
        """State with None values for optional fields doesn't crash."""
        state = {
            "character_roster": None,
            "world_context": None,
            "story_brief": None,
        }
        result = build_story_allowlist(state)
        assert result == set()

    def test_combines_all_sources(self):
        state = {
            "character_roster": CharacterRoster(
                characters=[
                    CharacterProfile(
                        character_id="c1",
                        name="Elias",
                        role=CharacterRole.PROTAGONIST,
                    ),
                ]
            ),
            "world_context": WorldContext(
                locations=[
                    Location(location_id="loc1", name="Beacon"),
                ]
            ),
            "story_brief": StoryBrief(
                title="Test",
                premise="A story",
                genre=Genre.SCI_FI,
                themes=["isolation"],
            ),
        }
        result = build_story_allowlist(state)
        assert "elias" in result
        assert "beacon" in result
        assert "isolation" in result
