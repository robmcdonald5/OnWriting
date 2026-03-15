"""Multi-strategy book discovery orchestrator.

Runs multiple discovery strategies (top-rated, most-read, priority author
search), deduplicates by book ID, and scores all results.
"""

import logging

from ai_writer.hardcover.client import HardcoverClient
from ai_writer.hardcover.schemas import DiscoveryReport, HardcoverBook, ScoredBook
from ai_writer.hardcover.scoring import BookScorer

logger = logging.getLogger("ai_writer.hardcover.discovery")

# Authors used for the priority_authors search strategy.
# These are searched to ensure coverage, but do NOT receive
# scoring bonuses — the scorer is author-agnostic.
# From training-data-sources.md sections 2-3.
SEARCH_AUTHORS: list[str] = sorted(
    {
        # Most-anthologized short story authors (section 3)
        "Raymond Carver",
        "Joyce Carol Oates",
        "John Updike",
        "Flannery O'Connor",
        "Richard Ford",
        "Tim O'Brien",
        "John Cheever",
        "Tobias Wolff",
        "Donald Barthelme",
        "James Baldwin",
        "William Faulkner",
        "Ernest Hemingway",
        "James Joyce",
        "Jamaica Kincaid",
        "Eudora Welty",
        # Authors cited as prose masters / award winners (sections 2-3)
        "Gustave Flaubert",
        "Vladimir Nabokov",
        "Toni Morrison",
        "Alice Munro",
        "Marilynne Robinson",
        "Cormac McCarthy",
        "Paul Harding",
        "Anthony Doerr",
        "George Saunders",
        "Colson Whitehead",
        "Jesmyn Ward",
        "Denis Johnson",
        "Hilary Mantel",
        "Kazuo Ishiguro",
        "Annie Proulx",
        "Anne Enright",
    }
)


class BookDiscovery:
    """Orchestrates multi-strategy book discovery and scoring.

    Strategies run sequentially with deduplication by book ID.
    After collection, all unique books are scored and sorted.

    Args:
        client: HardcoverClient instance for API access.
        scorer: BookScorer instance (optional, creates default if None).
    """

    def __init__(
        self,
        client: HardcoverClient,
        scorer: BookScorer | None = None,
    ):
        self._client = client
        self._scorer = scorer or BookScorer()
        self._seen_ids: set[int] = set()
        self._books: dict[int, tuple[HardcoverBook, str]] = {}

    def _add_books(self, books: list[HardcoverBook], source: str) -> int:
        """Add books to collection, deduplicating by ID.

        Args:
            books: Books to add.
            source: Discovery strategy name.

        Returns:
            Number of new (non-duplicate) books added.
        """
        new_count = 0
        for book in books:
            if book.id not in self._seen_ids:
                self._seen_ids.add(book.id)
                self._books[book.id] = (book, source)
                new_count += 1
        return new_count

    def run_top_rated(
        self, pages: int = 2, per_page: int = 50, min_ratings: int = 100
    ) -> int:
        """Discover books via top-rated strategy.

        Args:
            pages: Number of pages to fetch.
            per_page: Results per page.
            min_ratings: Minimum rating count filter.

        Returns:
            Number of new books found.
        """
        logger.info(
            "Strategy: top_rated (%d pages, min %d ratings)", pages, min_ratings
        )
        total_new = 0
        for page in range(pages):
            offset = page * per_page
            books = self._client.get_top_rated(
                min_ratings=min_ratings, limit=per_page, offset=offset
            )
            new = self._add_books(books, "top_rated")
            total_new += new
            logger.info("  Page %d: %d books (%d new)", page + 1, len(books), new)
        return total_new

    def run_most_read(
        self, pages: int = 2, per_page: int = 50, min_read: int = 500
    ) -> int:
        """Discover books via most-read strategy.

        Args:
            pages: Number of pages to fetch.
            per_page: Results per page.
            min_read: Minimum read count filter.

        Returns:
            Number of new books found.
        """
        logger.info("Strategy: most_read (%d pages, min %d reads)", pages, min_read)
        total_new = 0
        for page in range(pages):
            offset = page * per_page
            books = self._client.get_most_read(
                min_read=min_read, limit=per_page, offset=offset
            )
            new = self._add_books(books, "most_read")
            total_new += new
            logger.info("  Page %d: %d books (%d new)", page + 1, len(books), new)
        return total_new

    def run_priority_authors(
        self, per_author: int = 10, authors: list[str] | None = None
    ) -> int:
        """Discover books by searching for priority authors.

        Args:
            per_author: Results per author search.
            authors: Override author list (defaults to SEARCH_AUTHORS).

        Returns:
            Number of new books found.
        """
        author_list = authors or SEARCH_AUTHORS
        logger.info(
            "Strategy: priority_authors (%d authors, %d per author)",
            len(author_list),
            per_author,
        )
        total_new = 0
        for author in author_list:
            books = self._client.search_books(author, per_page=per_author)
            new = self._add_books(books, "priority_authors")
            total_new += new
            if new > 0:
                logger.info("  %s: %d books (%d new)", author, len(books), new)
        logger.info("  Total new from priority authors: %d", total_new)
        return total_new

    def run_all(self) -> DiscoveryReport:
        """Run all discovery strategies and return scored results.

        Strategies run in order: top_rated, most_read, priority_authors.

        Returns:
            DiscoveryReport with all scored books sorted by suitability.
        """
        strategies_used = []

        self.run_top_rated()
        strategies_used.append("top_rated")

        self.run_most_read()
        strategies_used.append("most_read")

        self.run_priority_authors()
        strategies_used.append("priority_authors")

        return self._build_report(strategies_used)

    def run_strategy(self, strategy: str) -> DiscoveryReport:
        """Run a single named strategy.

        Args:
            strategy: One of "top_rated", "most_read", "priority_authors".

        Returns:
            DiscoveryReport with scored results.

        Raises:
            ValueError: If strategy name is unknown.
        """
        strategy_map = {
            "top_rated": self.run_top_rated,
            "most_read": self.run_most_read,
            "priority_authors": self.run_priority_authors,
        }
        if strategy not in strategy_map:
            raise ValueError(
                f"Unknown strategy '{strategy}'. "
                f"Choose from: {', '.join(strategy_map)}"
            )

        strategy_map[strategy]()
        return self._build_report([strategy])

    def _build_report(self, strategies_used: list[str]) -> DiscoveryReport:
        """Score all collected books and build report.

        Args:
            strategies_used: List of strategy names that were run.

        Returns:
            Completed DiscoveryReport.
        """
        scored: list[ScoredBook] = []
        for book, source in self._books.values():
            scored.append(self._scorer.score_book(book, discovery_source=source))

        scored.sort(key=lambda s: s.total_score, reverse=True)

        report = DiscoveryReport(
            scored_books=scored,
            total_books_found=len(self._seen_ids),
            unique_books=len(self._seen_ids),
            api_calls_made=self._client.request_count,
            strategies_used=strategies_used,
        )

        logger.info(
            "Discovery complete: %d unique books, %d API calls",
            report.unique_books,
            report.api_calls_made,
        )

        return report
