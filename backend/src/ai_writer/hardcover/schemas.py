"""Pydantic models for Hardcover API data and scoring results."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HardcoverAuthor(BaseModel):
    """Author from Hardcover API."""

    name: str
    slug: str = ""


class HardcoverBook(BaseModel):
    """Book metadata from Hardcover API."""

    id: int
    title: str
    slug: str = ""
    rating: float = 0.0
    ratings_count: int = 0
    users_read_count: int = 0
    cached_tags: dict | None = None
    description: str = ""
    release_date: str | None = None
    authors: list[HardcoverAuthor] = Field(default_factory=list)
    isbn_13: str | None = None
    isbn_10: str | None = None
    pages: int | None = None

    @property
    def genres(self) -> list[str]:
        """Extract genre tags from cached_tags JSONB.

        Hardcover returns tags in two possible formats:
        - Object format: [{"tag": "Fiction", "category": "Genre", ...}, ...]
        - String format: ["Fiction", "Literary Fiction", ...]
        """
        if not self.cached_tags:
            return []
        for key in ("Genre", "genre", "Genres", "genres"):
            if key in self.cached_tags and isinstance(self.cached_tags[key], list):
                return self._extract_tag_names(self.cached_tags[key])
        return []

    @property
    def all_tags(self) -> list[str]:
        """Flatten all tag categories into a single list."""
        if not self.cached_tags:
            return []
        tags = []
        for value in self.cached_tags.values():
            if isinstance(value, list):
                tags.extend(self._extract_tag_names(value))
        return tags

    @staticmethod
    def _extract_tag_names(items: list) -> list[str]:
        """Extract tag name strings from a list of tag items.

        Handles both object format ({"tag": "Fiction", ...}) and
        plain string format ("Fiction").
        """
        names = []
        for item in items:
            if isinstance(item, dict) and "tag" in item:
                names.append(item["tag"])
            elif isinstance(item, str):
                names.append(item)
        return names

    @property
    def primary_isbn(self) -> str | None:
        """Return first available ISBN (prefer 13)."""
        return self.isbn_13 or self.isbn_10

    @property
    def author_names(self) -> list[str]:
        """Return list of author names."""
        return [a.name for a in self.authors]


class ScoredBook(BaseModel):
    """A book with its computed training-data suitability score."""

    book: HardcoverBook
    total_score: float = 0.0
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    discovery_source: str = ""


class DiscoveryReport(BaseModel):
    """Complete output of a book discovery run."""

    scored_books: list[ScoredBook] = Field(default_factory=list)
    total_books_found: int = 0
    unique_books: int = 0
    api_calls_made: int = 0
    strategies_used: list[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
