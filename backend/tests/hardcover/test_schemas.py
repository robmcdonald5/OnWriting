"""Tests for Hardcover schemas."""

from ai_writer.hardcover.schemas import (
    DiscoveryReport,
    HardcoverAuthor,
    HardcoverBook,
    ScoredBook,
)


class TestHardcoverBook:
    """Tests for HardcoverBook model."""

    def test_genres_from_cached_tags_strings(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            cached_tags={"Genre": ["Literary Fiction", "Short Stories"]},
        )
        assert book.genres == ["Literary Fiction", "Short Stories"]

    def test_genres_from_cached_tags_objects(self):
        """Real API format: genre tags are objects with a 'tag' field."""
        book = HardcoverBook(
            id=1,
            title="Test",
            cached_tags={
                "Genre": [
                    {"tag": "Literary Fiction", "tagSlug": "literary-fiction"},
                    {"tag": "Short Stories", "tagSlug": "short-stories"},
                ]
            },
        )
        assert book.genres == ["Literary Fiction", "Short Stories"]

    def test_genres_lowercase_key(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            cached_tags={"genre": ["Fiction"]},
        )
        assert book.genres == ["Fiction"]

    def test_genres_empty_when_no_tags(self):
        book = HardcoverBook(id=1, title="Test", cached_tags=None)
        assert book.genres == []

    def test_genres_empty_when_no_genre_key(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            cached_tags={"Subject": ["History"]},
        )
        assert book.genres == []

    def test_genres_empty_when_genre_not_list(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            cached_tags={"Genre": "Literary Fiction"},
        )
        assert book.genres == []

    def test_all_tags_flattens_categories(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            cached_tags={
                "Genre": ["Literary Fiction"],
                "Subject": ["History", "War"],
            },
        )
        assert set(book.all_tags) == {"Literary Fiction", "History", "War"}

    def test_all_tags_flattens_object_format(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            cached_tags={
                "Genre": [{"tag": "Fiction", "tagSlug": "fiction"}],
                "Mood": [{"tag": "Dark", "tagSlug": "dark"}],
                "Content Warning": [],
            },
        )
        assert set(book.all_tags) == {"Fiction", "Dark"}

    def test_primary_isbn_prefers_13(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            isbn_13="9780123456789",
            isbn_10="0123456789",
        )
        assert book.primary_isbn == "9780123456789"

    def test_primary_isbn_falls_back_to_10(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            isbn_10="0123456789",
        )
        assert book.primary_isbn == "0123456789"

    def test_primary_isbn_none_when_missing(self):
        book = HardcoverBook(id=1, title="Test")
        assert book.primary_isbn is None

    def test_author_names(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            authors=[
                HardcoverAuthor(name="Alice Smith"),
                HardcoverAuthor(name="Bob Jones"),
            ],
        )
        assert book.author_names == ["Alice Smith", "Bob Jones"]

    def test_author_names_empty(self):
        book = HardcoverBook(id=1, title="Test")
        assert book.author_names == []


class TestScoredBook:
    """Tests for ScoredBook model."""

    def test_score_bounds(self):
        book = HardcoverBook(id=1, title="Test")
        scored = ScoredBook(
            book=book,
            total_score=0.75,
            score_breakdown={"author_priority": 1.0, "genre_match": 0.5},
            discovery_source="test",
        )
        assert 0.0 <= scored.total_score <= 1.0
        assert scored.discovery_source == "test"

    def test_default_values(self):
        book = HardcoverBook(id=1, title="Test")
        scored = ScoredBook(book=book)
        assert scored.total_score == 0.0
        assert scored.score_breakdown == {}
        assert scored.discovery_source == ""


class TestDiscoveryReport:
    """Tests for DiscoveryReport model."""

    def test_default_construction(self):
        report = DiscoveryReport()
        assert report.scored_books == []
        assert report.total_books_found == 0
        assert report.unique_books == 0
        assert report.api_calls_made == 0
        assert report.strategies_used == []
        assert report.timestamp  # auto-set

    def test_with_data(self):
        book = HardcoverBook(id=1, title="Test")
        scored = ScoredBook(book=book, total_score=0.5)
        report = DiscoveryReport(
            scored_books=[scored],
            total_books_found=10,
            unique_books=8,
            api_calls_made=5,
            strategies_used=["top_rated"],
        )
        assert len(report.scored_books) == 1
        assert report.total_books_found == 10
