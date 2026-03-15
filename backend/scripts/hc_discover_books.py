"""Discover and rank books for training data acquisition via Hardcover API.

Usage:
    poetry run python scripts/hc_discover_books.py
    poetry run python scripts/hc_discover_books.py --top 50
    poetry run python scripts/hc_discover_books.py --output output/book_rankings.json
    poetry run python scripts/hc_discover_books.py --strategy priority_authors --verbose
    poetry run python scripts/hc_discover_books.py --min-score 0.5
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure backend/src is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_writer.config import get_settings
from ai_writer.hardcover.client import HardcoverClient
from ai_writer.hardcover.discovery import BookDiscovery
from ai_writer.hardcover.schemas import DiscoveryReport, ScoredBook
from ai_writer.logging_config import configure_logging


def print_table(scored_books: list[ScoredBook], top_n: int | None = None) -> None:
    """Print a ranked table of scored books to stdout."""
    books = scored_books[:top_n] if top_n else scored_books
    if not books:
        print("No books found.")
        return

    # Header
    print(
        f"{'Rank':>4}  {'Score':>5}  {'Title':<45}  {'Author':<25}  "
        f"{'Pages':>5}  {'ISBN':<14}  {'Rating':>6}  {'Reads':>7}  Genres"
    )
    print("-" * 160)

    for i, sb in enumerate(books, 1):
        book = sb.book
        title = book.title[:44] if len(book.title) > 44 else book.title
        author = ", ".join(book.author_names)[:24] if book.author_names else "Unknown"
        isbn = book.primary_isbn or "—"
        pages = str(book.pages) if book.pages else "—"
        genres = ", ".join(book.genres[:3]) if book.genres else "—"
        rating = f"{book.rating:.2f}" if book.rating > 0 else "—"
        reads = str(book.users_read_count) if book.users_read_count > 0 else "—"

        print(
            f"{i:>4}  {sb.total_score:>5.3f}  {title:<45}  {author:<25}  "
            f"{pages:>5}  {isbn:<14}  {rating:>6}  {reads:>7}  {genres}"
        )


def save_report(report: DiscoveryReport, output_path: str) -> None:
    """Save the full discovery report as JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, default=str)
    print(f"\nReport saved to: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Discover and rank books for training data via Hardcover API"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=25,
        help="Number of top results to display (default: 25)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to save full JSON report (e.g., output/book_rankings.json)",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["top_rated", "most_read", "priority_authors"],
        help="Run only a single strategy instead of all",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="Minimum score threshold for display (default: 0.0)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    configure_logging(level="DEBUG" if args.verbose else "INFO")

    settings = get_settings()
    if not settings.hardcover_api_key:
        print("Error: HARDCOVER_API_KEY not set in .env")
        sys.exit(1)

    client = HardcoverClient(api_key=settings.hardcover_api_key)
    discovery = BookDiscovery(client=client)

    print("Discovering books via Hardcover API...\n")

    if args.strategy:
        report = discovery.run_strategy(args.strategy)
    else:
        report = discovery.run_all()

    # Filter by minimum score
    if args.min_score > 0:
        report.scored_books = [
            sb for sb in report.scored_books if sb.total_score >= args.min_score
        ]

    print(
        f"\nFound {report.unique_books} unique books "
        f"({report.api_calls_made} API calls, "
        f"strategies: {', '.join(report.strategies_used)})\n"
    )

    print_table(report.scored_books, top_n=args.top)

    if args.output:
        save_report(report, args.output)


if __name__ == "__main__":
    main()
