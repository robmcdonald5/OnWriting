"""Scoring algorithm to rank books by training data suitability.

Scores books using genre-independent quality signals only:
awards (decomposed by type), count-weighted rating, description
language analysis, popularity as confidence, and publication era.

Author identity and genre classification are deliberately excluded —
they introduce confirmation bias and penalize high-quality prose
that happens to be shelved under genre fiction labels.
"""

import logging
import math
import re

from ai_writer.hardcover.schemas import HardcoverBook, ScoredBook

logger = logging.getLogger("ai_writer.hardcover.scoring")

# --- Award Tiers ---
# Decomposed by type: peer-judged prose awards are the strongest
# metadata signal for prose quality.

PROSE_AWARDS: list[str] = [
    "pen/faulkner",
    "pen faulkner",
    "o. henry",
    "o henry",
    "story prize",
    "pushcart",
    "national book critics circle",
]

MAJOR_LITERARY_AWARDS: list[str] = [
    "pulitzer",
    "national book award",
    "booker prize",
    "booker",
    "man booker",
    "nobel",
    "women's prize",
    "costa book",
    "kirkus prize",
]

# --- Description Language ---
# Prose-quality indicators vs plot-focused marketing language.
# Each match shifts the score from a 0.5 baseline.

PROSE_QUALITY_TERMS: list[str] = [
    "prose",
    "lyrical",
    "spare",
    "minimalist",
    "voice",
    "sentences",
    "literary",
    "crafted",
    "language",
    "stylistic",
    "poetic",
    "luminous",
    "elegiac",
    "meditative",
    "precise",
]

PLOT_FOCUSED_TERMS: list[str] = [
    "page-turner",
    "page turner",
    "twist",
    "shocking",
    "action-packed",
    "action packed",
    "thrilling",
    "edge of your seat",
    "unputdownable",
    "breakneck",
    "explosive",
    "blockbuster",
]

# --- Dimension Weights ---

WEIGHTS: dict[str, float] = {
    "award_signal": 0.35,
    "rating_quality": 0.25,
    "description_signal": 0.20,
    "popularity": 0.15,
    "era_bonus": 0.05,
}

# Minimum ratings for the rating score to be considered reliable
MIN_RATINGS_THRESHOLD = 50


def _score_award_signal(book: HardcoverBook) -> float:
    """Score 0.0-1.0 based on award mentions, decomposed by tier.

    Peer-judged prose awards (PEN/Faulkner, O. Henry, Story Prize)
    contribute more per match than major literary prizes, which are
    diluted by story/content criteria.
    """
    searchable = (book.description or "").lower()
    for tag in book.all_tags:
        searchable += " " + tag.lower()

    score = 0.0
    for keyword in PROSE_AWARDS:
        if keyword in searchable:
            score += 0.35
    for keyword in MAJOR_LITERARY_AWARDS:
        if keyword in searchable:
            score += 0.25
    return min(1.0, score)


def _score_rating_quality(book: HardcoverBook) -> float:
    """Score 0.0-1.0 based on count-weighted Hardcover rating.

    Ratings below MIN_RATINGS_THRESHOLD are unreliable and score 0.
    The 3.0-5.0 range is where meaningful differentiation happens
    (80% of books with significant readership cluster in 3.5-4.2).
    """
    if book.rating <= 0 or book.ratings_count < MIN_RATINGS_THRESHOLD:
        return 0.0
    return max(0.0, min(1.0, (book.rating - 3.0) / 2.0))


def _score_description_signal(book: HardcoverBook) -> float:
    """Score 0.0-1.0 based on description language analysis.

    Descriptions containing prose-quality terms ("lyrical", "spare",
    "voice-driven") indicate a book positioned on prose merit.
    Plot-focused terms ("page-turner", "twist", "shocking") indicate
    marketing on story rather than prose. Starts at 0.5 baseline.
    """
    if not book.description:
        return 0.5  # No signal, neutral
    desc = book.description.lower()

    score = 0.5
    for term in PROSE_QUALITY_TERMS:
        if term in desc:
            score += 0.15
    for term in PLOT_FOCUSED_TERMS:
        if term in desc:
            score -= 0.15
    return max(0.0, min(1.0, score))


def _score_popularity(book: HardcoverBook) -> float:
    """Score 0.0-1.0 based on read count (log scale, diminishing returns)."""
    if book.users_read_count <= 0:
        return 0.0
    return min(1.0, math.log10(book.users_read_count + 1) / 6.0)


def _score_era_bonus(book: HardcoverBook) -> float:
    """Score 0.0-1.0 based on publication era.

    Post-1950 = 1.0, 1900-1950 = 0.5, pre-1900 = 0.0.
    Modern prose reads more naturally for training data.
    """
    if not book.release_date:
        return 0.5  # Unknown era gets middle score
    match = re.search(r"(\d{4})", book.release_date)
    if not match:
        return 0.5
    year = int(match.group(1))
    if year >= 1950:
        return 1.0
    if year >= 1900:
        return 0.5
    return 0.0


class BookScorer:
    """Scores and ranks books by training data suitability.

    Each dimension produces a 0.0-1.0 raw score, then gets weighted.
    The total_score is the weighted sum (also 0.0-1.0).
    """

    def score_book(self, book: HardcoverBook, discovery_source: str = "") -> ScoredBook:
        """Compute training data suitability score for a single book.

        Args:
            book: Book to score.
            discovery_source: Which strategy found this book.

        Returns:
            ScoredBook with total score and per-dimension breakdown.
        """
        breakdown = {
            "award_signal": _score_award_signal(book),
            "rating_quality": _score_rating_quality(book),
            "description_signal": _score_description_signal(book),
            "popularity": _score_popularity(book),
            "era_bonus": _score_era_bonus(book),
        }

        total = sum(breakdown[dim] * WEIGHTS[dim] for dim in WEIGHTS)

        return ScoredBook(
            book=book,
            total_score=round(total, 4),
            score_breakdown=breakdown,
            discovery_source=discovery_source,
        )

    def score_books(
        self, books: list[HardcoverBook], discovery_source: str = ""
    ) -> list[ScoredBook]:
        """Score and sort a list of books by suitability (descending).

        Args:
            books: Books to score.
            discovery_source: Which strategy found these books.

        Returns:
            Sorted list of ScoredBooks (highest score first).
        """
        scored = [self.score_book(b, discovery_source) for b in books]
        scored.sort(key=lambda s: s.total_score, reverse=True)
        return scored
