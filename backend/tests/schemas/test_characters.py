"""Tests for character schemas."""

from ai_writer.schemas.characters import (
    CharacterProfile,
    CharacterRelationship,
    CharacterRole,
    CharacterRoster,
)


class TestCharacterProfile:
    def test_valid_construction(self):
        cp = CharacterProfile(
            character_id="c1",
            name="Alice",
            role=CharacterRole.PROTAGONIST,
        )
        assert cp.character_id == "c1"
        assert cp.name == "Alice"
        assert cp.personality_traits == []

    def test_all_roles(self):
        for role in CharacterRole:
            cp = CharacterProfile(character_id="x", name="Test", role=role)
            assert cp.role == role


class TestCharacterRoster:
    def _make_roster(self):
        chars = [
            CharacterProfile(
                character_id="c1", name="Hero", role=CharacterRole.PROTAGONIST
            ),
            CharacterProfile(
                character_id="c2", name="Villain", role=CharacterRole.ANTAGONIST
            ),
            CharacterProfile(
                character_id="c3", name="Sidekick", role=CharacterRole.SUPPORTING
            ),
        ]
        rels = [
            CharacterRelationship(
                from_character_id="c1",
                to_character_id="c2",
                relationship_type="nemesis",
            ),
        ]
        return CharacterRoster(characters=chars, relationships=rels)

    def test_get_character_found(self):
        roster = self._make_roster()
        assert roster.get_character("c1") is not None
        assert roster.get_character("c1").name == "Hero"

    def test_get_character_not_found(self):
        roster = self._make_roster()
        assert roster.get_character("nonexistent") is None

    def test_get_characters_by_role(self):
        roster = self._make_roster()
        protags = roster.get_characters_by_role(CharacterRole.PROTAGONIST)
        assert len(protags) == 1
        assert protags[0].name == "Hero"

    def test_empty_roster(self):
        roster = CharacterRoster()
        assert roster.characters == []
        assert roster.relationships == []
