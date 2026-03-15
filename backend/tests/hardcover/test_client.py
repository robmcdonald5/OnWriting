"""Tests for Hardcover API client."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from ai_writer.hardcover.client import HardcoverAPIError, HardcoverClient

# --- Fixtures ---


def _make_client(
    request_delay: float = 0,
) -> tuple[HardcoverClient, MagicMock]:
    """Create a client with an injectable mock session."""
    mock_session = MagicMock(spec=requests.Session)
    client = HardcoverClient(
        api_key="test-key", request_delay=request_delay, session=mock_session
    )
    return client, mock_session


def _mock_graphql_response(books: list[dict]) -> dict:
    """Build a mock GraphQL response with books."""
    return {"data": {"books": books}}


def _raw_book(
    book_id: int = 1,
    title: str = "Test Book",
    rating: float = 4.2,
    authors: list[dict] | None = None,
    isbn_13: str | None = "9780123456789",
) -> dict:
    """Build a raw book dict matching GraphQL response shape."""
    if authors is None:
        authors = [{"name": "Test Author", "slug": "test-author"}]
    return {
        "id": book_id,
        "title": title,
        "slug": title.lower().replace(" ", "-"),
        "rating": rating,
        "ratings_count": 500,
        "users_read_count": 1000,
        "cached_tags": {"Genre": ["Literary Fiction"]},
        "description": "A great book.",
        "release_date": "2020-01-01",
        "pages": 250,
        "contributions": [{"author": a} for a in authors],
        "editions": [{"isbn_13": isbn_13, "isbn_10": None}] if isbn_13 else [],
    }


# --- Constructor Tests ---


class TestClientConstruction:
    def test_requires_api_key(self):
        with pytest.raises(ValueError, match="API key is required"):
            HardcoverClient(api_key="")

    def test_constructs_with_key(self):
        client = HardcoverClient(api_key="test-key")
        assert client.request_count == 0

    def test_accepts_injected_session(self):
        mock_session = MagicMock(spec=requests.Session)
        client = HardcoverClient(api_key="test-key", session=mock_session)
        assert client._session is mock_session


# --- Parsing Tests ---


class TestParseBook:
    def test_parses_full_book(self):
        client = HardcoverClient(api_key="test-key")
        raw = _raw_book()
        book = client._parse_book(raw)
        assert book.id == 1
        assert book.title == "Test Book"
        assert book.rating == 4.2
        assert book.isbn_13 == "9780123456789"
        assert len(book.authors) == 1
        assert book.authors[0].name == "Test Author"

    def test_parses_missing_authors(self):
        client = HardcoverClient(api_key="test-key")
        raw = _raw_book()
        raw["contributions"] = None
        book = client._parse_book(raw)
        assert book.authors == []

    def test_parses_missing_editions(self):
        client = HardcoverClient(api_key="test-key")
        raw = _raw_book(isbn_13=None)
        raw["editions"] = []
        book = client._parse_book(raw)
        assert book.isbn_13 is None
        assert book.isbn_10 is None

    def test_parses_null_rating(self):
        client = HardcoverClient(api_key="test-key")
        raw = _raw_book()
        raw["rating"] = None
        book = client._parse_book(raw)
        assert book.rating == 0.0


# --- API Call Tests ---


class TestGetTopRated:
    def test_fetches_and_parses(self):
        client, mock_session = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = _mock_graphql_response(
            [_raw_book(1, "Book A"), _raw_book(2, "Book B")]
        )
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        books = client.get_top_rated(min_ratings=100, limit=50)

        assert len(books) == 2
        assert books[0].title == "Book A"
        assert books[1].title == "Book B"
        assert client.request_count == 1

    def test_empty_response(self):
        client, mock_session = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"books": []}}
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        books = client.get_top_rated()
        assert books == []


class TestGetMostRead:
    def test_fetches_and_parses(self):
        client, mock_session = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = _mock_graphql_response(
            [_raw_book(1, "Popular Book")]
        )
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        books = client.get_most_read(min_read=500, limit=50)
        assert len(books) == 1
        assert books[0].title == "Popular Book"


class TestSearchBooks:
    def test_parses_search_results(self):
        """Search is two-step: first gets IDs, then fetches full books."""
        client, mock_session = _make_client()
        # First call returns search IDs, second returns full book data
        search_response = MagicMock()
        search_response.json.return_value = {"data": {"search": {"ids": ["1"]}}}
        search_response.raise_for_status = MagicMock()

        book_response = MagicMock()
        book_response.json.return_value = _mock_graphql_response(
            [_raw_book(1, "Carver Collection")]
        )
        book_response.raise_for_status = MagicMock()

        mock_session.post.side_effect = [search_response, book_response]

        books = client.search_books("Raymond Carver", per_page=10)
        assert len(books) == 1
        assert books[0].title == "Carver Collection"
        assert client.request_count == 2  # search + fetch

    def test_empty_search_returns_empty(self):
        client, mock_session = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"search": {"ids": []}}}
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        books = client.search_books("Nonexistent Author")
        assert books == []
        assert client.request_count == 1  # Only search, no fetch

    def test_skips_non_numeric_ids(self):
        """Non-numeric IDs in search results are skipped."""
        client, mock_session = _make_client()
        search_response = MagicMock()
        search_response.json.return_value = {
            "data": {"search": {"ids": ["1", "abc", "3"]}}
        }
        search_response.raise_for_status = MagicMock()

        book_response = MagicMock()
        book_response.json.return_value = _mock_graphql_response(
            [_raw_book(1, "Book One"), _raw_book(3, "Book Three")]
        )
        book_response.raise_for_status = MagicMock()

        mock_session.post.side_effect = [search_response, book_response]

        books = client.search_books("Test Author")
        assert len(books) == 2

    def test_all_non_numeric_ids_returns_empty(self):
        """If all search IDs are non-numeric, return empty list."""
        client, mock_session = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"search": {"ids": ["abc", "def"]}}}
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        books = client.search_books("Test Author")
        assert books == []
        assert client.request_count == 1  # Only search, no fetch


class TestGetBooksByIds:
    def test_fetches_by_ids(self):
        client, mock_session = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = _mock_graphql_response(
            [_raw_book(42, "Specific Book")]
        )
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        books = client.get_books_by_ids([42])
        assert len(books) == 1
        assert books[0].id == 42


class TestGetList:
    def test_fetches_list_books(self):
        client, mock_session = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "lists_by_pk": {"list_books": [{"book": _raw_book(1, "List Book")}]}
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        books = client.get_list(list_id=123)
        assert len(books) == 1
        assert books[0].title == "List Book"

    def test_handles_null_list(self):
        client, mock_session = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"lists_by_pk": None}}
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        books = client.get_list(list_id=999)
        assert books == []


# --- Error Handling ---


class TestErrorHandling:
    def test_raises_on_graphql_errors(self):
        client, mock_session = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"errors": [{"message": "Field not found"}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        with pytest.raises(HardcoverAPIError, match="Field not found"):
            client.get_top_rated()

    def test_request_count_increments(self):
        client, mock_session = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = _mock_graphql_response([_raw_book()])
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        assert client.request_count == 0
        client.get_top_rated()
        assert client.request_count == 1
        client.get_top_rated()
        assert client.request_count == 2


class TestPartialData:
    def test_partial_data_returned_when_errors_coexist(self):
        """When GraphQL returns both errors and data, use the data."""
        client, mock_session = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "errors": [{"message": "Partial failure"}],
            "data": {"books": [_raw_book(1, "Partial Book")]},
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        books = client.get_top_rated()
        assert len(books) == 1
        assert books[0].title == "Partial Book"

    def test_raises_when_errors_without_data(self):
        """When GraphQL returns errors but no data, raise."""
        client, mock_session = _make_client()
        mock_response = MagicMock()
        mock_response.json.return_value = {"errors": [{"message": "Total failure"}]}
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        with pytest.raises(HardcoverAPIError, match="Total failure"):
            client.get_top_rated()


class TestHTTPErrors:
    def test_raises_on_http_error(self):
        client, mock_session = _make_client()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "500 Server Error"
        )
        mock_session.post.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            client.get_top_rated()

    def test_raises_on_connection_error(self):
        client, mock_session = _make_client()
        mock_session.post.side_effect = requests.ConnectionError("Connection refused")

        with pytest.raises(requests.ConnectionError):
            client.get_top_rated()

    def test_raises_on_timeout(self):
        client, mock_session = _make_client()
        mock_session.post.side_effect = requests.Timeout("Request timed out")

        with pytest.raises(requests.Timeout):
            client.get_top_rated()


# --- Rate Limiting ---


class TestRateLimiting:
    @patch("ai_writer.hardcover.client.time.sleep")
    def test_rate_limits_between_requests(self, mock_sleep):
        client, mock_session = _make_client(request_delay=1.0)
        mock_response = MagicMock()
        mock_response.json.return_value = _mock_graphql_response([_raw_book()])
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        client.get_top_rated()
        client.get_top_rated()

        assert mock_sleep.called
        sleep_duration = mock_sleep.call_args[0][0]
        assert 0 < sleep_duration <= 1.0

    @patch("ai_writer.hardcover.client.time.sleep")
    def test_no_rate_limit_on_first_request(self, mock_sleep):
        client, mock_session = _make_client(request_delay=1.0)
        mock_response = MagicMock()
        mock_response.json.return_value = _mock_graphql_response([_raw_book()])
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        client.get_top_rated()
        assert not mock_sleep.called
