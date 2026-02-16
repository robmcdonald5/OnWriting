"""Character schemas for casting and relationship tracking."""

from enum import Enum

from pydantic import BaseModel, Field


class CharacterRole(str, Enum):
    """Standard character roles in a story."""

    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    MENTOR = "mentor"
    SUPPORTING = "supporting"
    LOVE_INTEREST = "love_interest"
    COMIC_RELIEF = "comic_relief"
    CONFIDANT = "confidant"
    FOIL = "foil"


class CharacterProfile(BaseModel):
    """Complete character profile for consistent writing."""

    character_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    role: CharacterRole
    description: str = Field(default="")
    personality_traits: list[str] = Field(default_factory=list)
    motivation: str = Field(default="")
    internal_conflict: str = Field(default="")
    backstory_summary: str = Field(default="")
    voice_notes: str = Field(
        default="",
        description="How this character speaks — dialect, vocabulary, cadence",
    )
    speech_patterns: list[str] = Field(
        default_factory=list,
        description="Example phrases or verbal tics",
    )


class CharacterRelationship(BaseModel):
    """Directed relationship between two characters."""

    from_character_id: str = Field(min_length=1)
    to_character_id: str = Field(min_length=1)
    relationship_type: str = Field(min_length=1)
    description: str = Field(default="")


class CharacterRoster(BaseModel):
    """The full cast of characters with their relationships."""

    characters: list[CharacterProfile] = Field(default_factory=list)
    relationships: list[CharacterRelationship] = Field(default_factory=list)

    def get_character(self, character_id: str) -> CharacterProfile | None:
        """Look up a character by ID."""
        for c in self.characters:
            if c.character_id == character_id:
                return c
        return None

    def get_characters_by_role(self, role: CharacterRole) -> list[CharacterProfile]:
        """Get all characters with a given role."""
        return [c for c in self.characters if c.role == role]
