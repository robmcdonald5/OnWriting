"""HTTP client wrapper for the Hardcover GraphQL API."""

import logging
import time

import requests

from ai_writer.hardcover.schemas import HardcoverAuthor, HardcoverBook

logger = logging.getLogger("ai_writer.hardcover.client")

API_URL = "https://api.hardcover.app/v1/graphql"
REQUEST_DELAY = 1.0  # seconds between requests (60 req/min limit)


class HardcoverAPIError(Exception):
    """Raised when the Hardcover API returns an error response."""


class HardcoverClient:
    """Client for the Hardcover GraphQL API with rate limiting.

    Args:
        api_key: Hardcover API bearer token.
        request_delay: Seconds to wait between requests.
    """

    def __init__(self, api_key: str, request_delay: float = REQUEST_DELAY):
        if not api_key:
            raise ValueError("Hardcover API key is required")
        self._api_key = api_key
        self._request_delay = request_delay
        self._last_request_time: float = 0.0
        self._request_count = 0

    @property
    def request_count(self) -> int:
        """Total API requests made by this client instance."""
        return self._request_count

    def _rate_limit(self) -> None:
        """Enforce minimum delay between requests."""
        if self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._request_delay:
                wait = self._request_delay - elapsed
                logger.debug("Rate limiting: waiting %.2fs", wait)
                time.sleep(wait)

    def _execute(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query against the Hardcover API.

        Args:
            query: GraphQL query string.
            variables: Query variables.

        Returns:
            The 'data' portion of the GraphQL response.

        Raises:
            HardcoverAPIError: If the API returns errors.
            requests.RequestException: On network failures.
        """
        self._rate_limit()

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables

        logger.debug("Executing GraphQL query (request #%d)", self._request_count + 1)

        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        self._last_request_time = time.time()
        self._request_count += 1

        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            error_messages = [e.get("message", str(e)) for e in result["errors"]]
            raise HardcoverAPIError(f"GraphQL errors: {'; '.join(error_messages)}")

        return result.get("data", {})

    def _parse_book(self, raw: dict) -> HardcoverBook:
        """Normalize raw GraphQL book JSON into a HardcoverBook.

        Args:
            raw: Raw book dict from GraphQL response.

        Returns:
            Parsed HardcoverBook instance.
        """
        authors = []
        for contrib in raw.get("contributions", []) or []:
            author_data = contrib.get("author", {})
            if author_data and author_data.get("name"):
                authors.append(
                    HardcoverAuthor(
                        name=author_data["name"],
                        slug=author_data.get("slug", ""),
                    )
                )

        isbn_13 = None
        isbn_10 = None
        editions = raw.get("editions", []) or []
        if editions:
            isbn_13 = editions[0].get("isbn_13")
            isbn_10 = editions[0].get("isbn_10")

        return HardcoverBook(
            id=raw.get("id", 0),
            title=raw.get("title", ""),
            slug=raw.get("slug", ""),
            rating=raw.get("rating") or 0.0,
            ratings_count=raw.get("ratings_count") or 0,
            users_read_count=raw.get("users_read_count") or 0,
            cached_tags=raw.get("cached_tags"),
            description=raw.get("description") or "",
            release_date=raw.get("release_date"),
            authors=authors,
            isbn_13=isbn_13,
            isbn_10=isbn_10,
            pages=raw.get("pages"),
        )

    def get_top_rated(
        self, min_ratings: int = 100, limit: int = 50, offset: int = 0
    ) -> list[HardcoverBook]:
        """Fetch top-rated books.

        Args:
            min_ratings: Minimum number of ratings required.
            limit: Number of results per page.
            offset: Pagination offset.

        Returns:
            List of parsed books.
        """
        from ai_writer.hardcover.queries import TOP_RATED_BOOKS

        data = self._execute(
            TOP_RATED_BOOKS,
            {"min_ratings": min_ratings, "limit": limit, "offset": offset},
        )
        return [self._parse_book(b) for b in data.get("books", [])]

    def get_most_read(
        self, min_read: int = 500, limit: int = 50, offset: int = 0
    ) -> list[HardcoverBook]:
        """Fetch most-read books.

        Args:
            min_read: Minimum read count required.
            limit: Number of results per page.
            offset: Pagination offset.

        Returns:
            List of parsed books.
        """
        from ai_writer.hardcover.queries import MOST_READ_BOOKS

        data = self._execute(
            MOST_READ_BOOKS,
            {"min_read": min_read, "limit": limit, "offset": offset},
        )
        return [self._parse_book(b) for b in data.get("books", [])]

    def search_books(self, query: str, per_page: int = 10) -> list[HardcoverBook]:
        """Search books by text query (typically author name).

        Two-step: search returns IDs, then fetches full book data.

        Args:
            query: Search text.
            per_page: Number of results.

        Returns:
            List of parsed books.
        """
        from ai_writer.hardcover.queries import SEARCH_BOOKS

        data = self._execute(SEARCH_BOOKS, {"query": query, "per_page": per_page})
        search_data = data.get("search", {})
        raw_ids = search_data.get("ids", [])
        if not raw_ids:
            return []
        # Search returns IDs as strings; convert to ints for book fetch
        int_ids = [int(id_val) for id_val in raw_ids]
        return self.get_books_by_ids(int_ids)

    def get_books_by_ids(self, ids: list[int]) -> list[HardcoverBook]:
        """Fetch books by their Hardcover IDs.

        Args:
            ids: List of book IDs to fetch.

        Returns:
            List of parsed books.
        """
        from ai_writer.hardcover.queries import BOOK_BY_IDS

        data = self._execute(BOOK_BY_IDS, {"ids": ids})
        return [self._parse_book(b) for b in data.get("books", [])]

    def get_list(self, list_id: int) -> list[HardcoverBook]:
        """Fetch books from a curated Hardcover list.

        Args:
            list_id: Hardcover list ID.

        Returns:
            List of parsed books.
        """
        from ai_writer.hardcover.queries import LIST_BOOKS

        data = self._execute(LIST_BOOKS, {"id": list_id})
        list_data = data.get("lists_by_pk") or {}
        list_books = list_data.get("list_books", [])
        return [self._parse_book(lb.get("book", {})) for lb in list_books]
