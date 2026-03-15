"""Tests for book scoring algorithm."""

from ai_writer.hardcover.schemas import HardcoverAuthor, HardcoverBook
from ai_writer.hardcover.scoring import (
    WEIGHTS,
    BookScorer,
    _score_award_signal,
    _score_description_signal,
    _score_era_bonus,
    _score_popularity,
    _score_rating_quality,
)

# --- Award Signal Tests ---


class TestAwardSignal:
    def test_prose_award_scores_high(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            description="Winner of the PEN/Faulkner Award",
        )
        assert _score_award_signal(book) == 0.35

    def test_major_literary_award(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            description="Winner of the Pulitzer Prize",
        )
        assert _score_award_signal(book) == 0.25

    def test_prose_award_weighted_higher_than_major(self):
        prose_book = HardcoverBook(
            id=1,
            title="A",
            description="Won the O. Henry Prize",
        )
        major_book = HardcoverBook(
            id=2,
            title="B",
            description="Won the Pulitzer Prize",
        )
        assert _score_award_signal(prose_book) > _score_award_signal(major_book)

    def test_multiple_awards_combine(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            description="Won the Pulitzer Prize and the National Book Award",
        )
        assert _score_award_signal(book) == 0.5

    def test_many_awards_cap_at_1(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            description="Pulitzer, National Book Award, Booker Prize, Nobel, PEN/Faulkner, O. Henry",
        )
        assert _score_award_signal(book) == 1.0

    def test_no_awards(self):
        book = HardcoverBook(id=1, title="Test", description="A nice book about cats.")
        assert _score_award_signal(book) == 0.0

    def test_award_in_tags(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            cached_tags={"Award": ["Booker Prize Winner"]},
        )
        assert _score_award_signal(book) >= 0.25

    def test_no_false_positive_for_nobel_substring(self):
        """'nobel' should not match inside 'nobelist'."""
        book = HardcoverBook(
            id=1,
            title="Test",
            description="A nobelist's journey through life",
        )
        assert _score_award_signal(book) == 0.0

    def test_no_false_positive_for_booker_substring(self):
        """'booker' should not match inside 'Bookermans'."""
        book = HardcoverBook(
            id=1,
            title="Test",
            cached_tags={"Genre": ["Bookermans Guide"]},
        )
        assert _score_award_signal(book) == 0.0


# --- Rating Quality Tests ---


class TestRatingQuality:
    def test_high_rating_high_count(self):
        book = HardcoverBook(id=1, title="Test", rating=5.0, ratings_count=500)
        assert _score_rating_quality(book) == 1.0

    def test_mid_rating_sufficient_count(self):
        book = HardcoverBook(id=1, title="Test", rating=4.0, ratings_count=100)
        assert _score_rating_quality(book) == 0.5

    def test_low_rating(self):
        book = HardcoverBook(id=1, title="Test", rating=3.0, ratings_count=200)
        assert _score_rating_quality(book) == 0.0

    def test_below_min_count_scores_0(self):
        """Books with too few ratings get 0 — the rating is unreliable."""
        book = HardcoverBook(id=1, title="Test", rating=4.8, ratings_count=10)
        assert _score_rating_quality(book) == 0.0

    def test_exactly_at_threshold(self):
        book = HardcoverBook(id=1, title="Test", rating=4.0, ratings_count=50)
        assert _score_rating_quality(book) == 0.5

    def test_zero_rating(self):
        book = HardcoverBook(id=1, title="Test", rating=0.0, ratings_count=100)
        assert _score_rating_quality(book) == 0.0


# --- Description Signal Tests ---


class TestDescriptionSignal:
    def test_prose_quality_terms_increase_score(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            description="A lyrical and spare novel with luminous prose",
        )
        score = _score_description_signal(book)
        assert score > 0.5

    def test_plot_focused_terms_decrease_score(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            description="A thrilling page-turner with a shocking twist",
        )
        score = _score_description_signal(book)
        assert score < 0.5

    def test_neutral_description_scores_baseline(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            description="A novel about a family in Ohio.",
        )
        assert _score_description_signal(book) == 0.5

    def test_no_description_scores_baseline(self):
        book = HardcoverBook(id=1, title="Test", description="")
        assert _score_description_signal(book) == 0.5

    def test_mixed_terms_balance(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            description="A lyrical page-turner",
        )
        # One positive + one negative = back to baseline
        assert _score_description_signal(book) == 0.5

    def test_capped_at_1(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            description="Lyrical spare minimalist prose with crafted poetic luminous meditative precise sentences in elegant stylistic language",
        )
        assert _score_description_signal(book) == 1.0

    def test_capped_at_0(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            description="A thrilling page-turner, action-packed and shocking with explosive breakneck blockbuster twist",
        )
        assert _score_description_signal(book) == 0.0

    def test_no_false_positive_voice_in_invoice(self):
        """'voice' should not match inside 'invoice'."""
        book = HardcoverBook(
            id=1,
            title="Test",
            description="An invoice processing system",
        )
        assert _score_description_signal(book) == 0.5

    def test_no_false_positive_crafted_in_handcrafted(self):
        """'crafted' should not match inside 'handcrafted'."""
        book = HardcoverBook(
            id=1,
            title="Test",
            description="A story about handcrafted items",
        )
        assert _score_description_signal(book) == 0.5


# --- Popularity Tests ---


class TestPopularity:
    def test_very_popular(self):
        book = HardcoverBook(id=1, title="Test", users_read_count=1_000_000)
        assert _score_popularity(book) == 1.0

    def test_moderately_popular(self):
        book = HardcoverBook(id=1, title="Test", users_read_count=1000)
        score = _score_popularity(book)
        assert 0.0 < score < 1.0

    def test_no_reads(self):
        book = HardcoverBook(id=1, title="Test", users_read_count=0)
        assert _score_popularity(book) == 0.0


# --- Era Bonus Tests ---


class TestEraBonus:
    def test_modern_book(self):
        book = HardcoverBook(id=1, title="Test", release_date="2020-01-01")
        assert _score_era_bonus(book) == 1.0

    def test_mid_century(self):
        book = HardcoverBook(id=1, title="Test", release_date="1925-01-01")
        assert _score_era_bonus(book) == 0.5

    def test_old_book(self):
        book = HardcoverBook(id=1, title="Test", release_date="1850-01-01")
        assert _score_era_bonus(book) == 0.0

    def test_no_date_gets_middle(self):
        book = HardcoverBook(id=1, title="Test", release_date=None)
        assert _score_era_bonus(book) == 0.5

    def test_year_only_string(self):
        book = HardcoverBook(id=1, title="Test", release_date="1960")
        assert _score_era_bonus(book) == 1.0

    def test_non_year_leading_digits(self):
        """Non-year digit strings at start should not extract a year."""
        book = HardcoverBook(id=1, title="Test", release_date="ISBN9780")
        assert _score_era_bonus(book) == 0.5


# --- Scorer Integration Tests ---


class TestBookScorer:
    def test_weights_sum_to_1(self):
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_award_winning_book_scores_high(self):
        """A book with multiple awards, good rating, prose-focused description."""
        book = HardcoverBook(
            id=1,
            title="Gilead",
            authors=[HardcoverAuthor(name="Marilynne Robinson")],
            cached_tags={"Genre": ["Literary Fiction"]},
            rating=4.5,
            ratings_count=5000,
            users_read_count=50000,
            description="Winner of the Pulitzer Prize. A lyrical, meditative novel with spare, luminous prose.",
            release_date="2004-01-01",
            pages=247,
        )
        scorer = BookScorer()
        scored = scorer.score_book(book)
        assert scored.total_score > 0.6

    def test_plot_driven_genre_fiction_scores_lower(self):
        """A plot-focused book with no awards and marketing-driven description."""
        book = HardcoverBook(
            id=2,
            title="Dragon's Quest",
            authors=[HardcoverAuthor(name="Unknown Fantasy Writer")],
            cached_tags={"Genre": ["Fantasy", "Young Adult"]},
            rating=3.5,
            ratings_count=200,
            users_read_count=500,
            description="A thrilling page-turner with a shocking twist!",
            release_date="2022-01-01",
        )
        scorer = BookScorer()
        scored = scorer.score_book(book)
        assert scored.total_score < 0.3

    def test_genre_fiction_with_awards_not_penalized(self):
        """Genre fiction with strong independent quality signals should score well.

        This is the key test: a sci-fi novel with a Pulitzer should not be
        penalized for its genre tag. The old scoring would give this 0.1
        for genre; the new scoring is genre-agnostic.
        """
        book = HardcoverBook(
            id=3,
            title="The Road",
            authors=[HardcoverAuthor(name="Cormac McCarthy")],
            cached_tags={"Genre": ["Science Fiction", "Post-Apocalyptic"]},
            rating=4.3,
            ratings_count=8000,
            users_read_count=30000,
            description="Winner of the Pulitzer Prize. Spare, meditative prose.",
            release_date="2006-01-01",
        )
        scorer = BookScorer()
        scored = scorer.score_book(book)
        # Should score well despite genre tags
        assert scored.total_score > 0.5

    def test_unknown_author_with_awards_scores_well(self):
        """An unknown author with strong quality signals should rank highly.

        This tests the discovery value: author identity should not gate scoring.
        """
        book = HardcoverBook(
            id=4,
            title="Debut Novel",
            authors=[HardcoverAuthor(name="Completely Unknown Writer")],
            rating=4.4,
            ratings_count=300,
            users_read_count=2000,
            description="Winner of the PEN/Faulkner Award. Lyrical, crafted prose.",
            release_date="2023-01-01",
        )
        scorer = BookScorer()
        scored = scorer.score_book(book)
        assert scored.total_score > 0.5

    def test_score_books_sorts_descending(self):
        good = HardcoverBook(
            id=1,
            title="Award Winner",
            rating=4.5,
            ratings_count=500,
            description="Winner of the Pulitzer Prize. Luminous prose.",
        )
        bad = HardcoverBook(
            id=2,
            title="No Signals",
            rating=3.0,
            ratings_count=10,
        )
        scorer = BookScorer()
        results = scorer.score_books([bad, good])
        assert results[0].book.title == "Award Winner"
        assert results[1].book.title == "No Signals"

    def test_discovery_source_preserved(self):
        book = HardcoverBook(id=1, title="Test")
        scorer = BookScorer()
        scored = scorer.score_book(book, discovery_source="top_rated")
        assert scored.discovery_source == "top_rated"

    def test_all_dimensions_in_breakdown(self):
        book = HardcoverBook(id=1, title="Test")
        scorer = BookScorer()
        scored = scorer.score_book(book)
        for dim in WEIGHTS:
            assert dim in scored.score_breakdown

    def test_score_bounded_0_to_1(self):
        book = HardcoverBook(
            id=1,
            title="Test",
            rating=5.0,
            ratings_count=10000,
            users_read_count=10_000_000,
            description="Pulitzer National Book Award Booker Nobel PEN/Faulkner. Lyrical spare prose.",
            release_date="2024-01-01",
        )
        scorer = BookScorer()
        scored = scorer.score_book(book)
        assert 0.0 <= scored.total_score <= 1.0
        for value in scored.score_breakdown.values():
            assert 0.0 <= value <= 1.0

    def test_no_author_or_genre_dimensions(self):
        """Verify author_priority and genre_match are not in the scoring."""
        assert "author_priority" not in WEIGHTS
        assert "genre_match" not in WEIGHTS
