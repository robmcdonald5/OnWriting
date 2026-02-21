"""Story-aware allowlist extraction for slop false-positive suppression.

Extracts character names, location names, and theme words from the pipeline
state so they can be excluded from slop detection. This prevents character
names like "Elias" from being flagged when they happen to overlap with
phrases in the slop database.
"""

from __future__ import annotations

from typing import Any


def build_story_allowlist(state: dict[str, Any]) -> set[str]:
    """Extract story-specific terms that should not be flagged as slop.

    Sources:
    - Character names (full name + individual parts)
    - Location names (full name + individual parts)
    - Theme words (>3 chars, lowercased)

    Returns:
        A set of lowercased terms to exclude from slop detection.
    """
    terms: set[str] = set()

    # Character names
    roster = state.get("character_roster")
    if roster is not None:
        for char in roster.characters:
            name = char.name.strip()
            if name:
                terms.add(name.lower())
                for part in name.split():
                    part = part.strip()
                    if len(part) > 2:
                        terms.add(part.lower())

    # Location names
    world = state.get("world_context")
    if world is not None:
        for loc in world.locations:
            name = loc.name.strip()
            if name:
                terms.add(name.lower())
                for part in name.split():
                    part = part.strip()
                    if len(part) > 2:
                        terms.add(part.lower())

    # Theme words
    brief = state.get("story_brief")
    if brief is not None:
        for theme in brief.themes:
            for word in theme.split():
                word = word.strip().lower()
                if len(word) > 3:
                    terms.add(word)

    return terms
