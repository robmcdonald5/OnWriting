"""Worldbuilding schemas for setting and lore."""

from pydantic import BaseModel, Field


class Location(BaseModel):
    """A specific location in the story world."""

    location_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(default="")
    significance: str = Field(
        default="", description="Why this location matters to the story"
    )


class WorldRule(BaseModel):
    """A rule or constraint of the story world."""

    rule_id: str = Field(min_length=1)
    category: str = Field(
        default="general",
        description="e.g. magic_system, technology, social, physical",
    )
    statement: str = Field(min_length=1)
    implications: list[str] = Field(default_factory=list)


class WorldContext(BaseModel):
    """The complete worldbuilding context for the story."""

    setting_period: str = Field(default="")
    setting_description: str = Field(default="")
    locations: list[Location] = Field(default_factory=list)
    rules: list[WorldRule] = Field(default_factory=list)
    key_facts: list[str] = Field(default_factory=list)
