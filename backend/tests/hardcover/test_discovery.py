"""Tests for book discovery orchestrator."""

from unittest.mock import MagicMock

import pytest

from ai_writer.hardcover.client import HardcoverClient
from ai_writer.hardcover.discovery import BookDiscovery
from ai_writer.hardcover.schemas import HardcoverAuthor, HardcoverBook
from ai_writer.hardcover.scoring import BookScorer


# --- Helpers ---


def _make_book(book_id: int, title: str = "Test", **kwargs) -> HardcoverBook:
    return HardcoverBook(id=book_id, title=title, **kwargs)


def _mock_client() -> MagicMock:
    """Create a mock HardcoverClient with default return values."""
    client = MagicMock(spec=HardcoverClient)
    client.request_count = 0

    # Default: return empty lists
    client.get_top_rated.return_value = []
    client.get_most_read.return_value = []
    client.search_books.return_value = []
    client.get_books_by_ids.return_value = []
    client.get_list.return_value = []
    return client


# --- Deduplication Tests ---


class TestDeduplication:
    def test_deduplicates_by_book_id(self):
        client = _mock_client()
        book = _make_book(1, "Duplicate")
        client.get_top_rated.return_value = [book]
        client.get_most_read.return_value = [book]  # Same ID

        discovery = BookDiscovery(client=client)
        discovery.run_top_rated(pages=1)
        discovery.run_most_read(pages=1)

        report = discovery._build_report(["top_rated", "most_read"])
        assert report.unique_books == 1

    def test_keeps_different_books(self):
        client = _mock_client()
        client.get_top_rated.return_value = [_make_book(1, "Book A")]
        client.get_most_read.return_value = [_make_book(2, "Book B")]

        discovery = BookDiscovery(client=client)
        discovery.run_top_rated(pages=1)
        discovery.run_most_read(pages=1)

        report = discovery._build_report(["top_rated", "most_read"])
        assert report.unique_books == 2

    def test_preserves_first_source(self):
        client = _mock_client()
        book = _make_book(1, "Found Twice")
        client.get_top_rated.return_value = [book]
        client.get_most_read.return_value = [book]

        discovery = BookDiscovery(client=client)
        discovery.run_top_rated(pages=1)
        discovery.run_most_read(pages=1)

        report = discovery._build_report(["top_rated", "most_read"])
        assert report.scored_books[0].discovery_source == "top_rated"


# --- Strategy Tests ---


class TestStrategies:
    def test_top_rated_calls_client(self):
        client = _mock_client()
        client.get_top_rated.return_value = [_make_book(1)]

        discovery = BookDiscovery(client=client)
        new = discovery.run_top_rated(pages=2, per_page=50, min_ratings=100)

        assert client.get_top_rated.call_count == 2
        assert new == 1  # Same book returned both times, deduped

    def test_most_read_calls_client(self):
        client = _mock_client()
        client.get_most_read.return_value = [_make_book(1)]

        discovery = BookDiscovery(client=client)
        new = discovery.run_most_read(pages=1, per_page=50)

        assert client.get_most_read.call_count == 1
        assert new == 1

    def test_priority_authors_searches_each(self):
        client = _mock_client()
        # Return a unique book per author
        call_count = 0

        def search_side_effect(query, per_page=10):
            nonlocal call_count
            call_count += 1
            return [_make_book(call_count, f"Book by {query}")]

        client.search_books.side_effect = search_side_effect

        discovery = BookDiscovery(client=client)
        authors = ["Raymond Carver", "Flannery O'Connor", "James Baldwin"]
        new = discovery.run_priority_authors(per_author=10, authors=authors)

        assert client.search_books.call_count == 3
        assert new == 3


# --- Run All Tests ---


class TestRunAll:
    def test_run_all_executes_all_strategies(self):
        client = _mock_client()
        client.get_top_rated.return_value = [_make_book(1, "Top Book")]
        client.get_most_read.return_value = [_make_book(2, "Popular Book")]
        client.search_books.return_value = [_make_book(3, "Author Book")]

        discovery = BookDiscovery(client=client)
        report = discovery.run_all()

        assert "top_rated" in report.strategies_used
        assert "most_read" in report.strategies_used
        assert "priority_authors" in report.strategies_used
        assert report.unique_books == 3

    def test_run_all_scores_are_sorted(self):
        client = _mock_client()
        # High-scoring book (award winner, high rating, prose-focused)
        good_book = _make_book(
            1,
            "Award Winner",
            rating=4.5,
            ratings_count=500,
            description="Winner of the Pulitzer Prize. Lyrical, spare prose.",
        )
        # Low-scoring book (no awards, low rating count)
        bad_book = _make_book(
            2,
            "Generic Book",
            rating=3.0,
            ratings_count=10,
        )
        client.get_top_rated.return_value = [bad_book, good_book]

        discovery = BookDiscovery(client=client)
        discovery.run_top_rated(pages=1)
        report = discovery._build_report(["top_rated"])

        assert report.scored_books[0].book.title == "Award Winner"


# --- Single Strategy Tests ---


class TestRunStrategy:
    def test_run_single_strategy(self):
        client = _mock_client()
        client.get_top_rated.return_value = [_make_book(1)]

        discovery = BookDiscovery(client=client)
        report = discovery.run_strategy("top_rated")

        assert report.strategies_used == ["top_rated"]
        assert report.unique_books == 1

    def test_invalid_strategy_raises(self):
        client = _mock_client()
        discovery = BookDiscovery(client=client)

        with pytest.raises(ValueError, match="Unknown strategy"):
            discovery.run_strategy("nonexistent")


# --- Report Tests ---


class TestReport:
    def test_report_metadata(self):
        client = _mock_client()
        client.request_count = 5

        discovery = BookDiscovery(client=client)
        report = discovery._build_report(["top_rated"])

        assert report.api_calls_made == 5
        assert report.strategies_used == ["top_rated"]
        assert report.timestamp  # auto-set
