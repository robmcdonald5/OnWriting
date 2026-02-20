"""Tests for weighted slop detection using sam-paech data."""

from ai_writer.utils.text_analysis import compute_slop_score


class TestComputeSlopScore:
    def test_clean_prose_scores_high(self):
        prose = (
            "The old station creaked in the void. Commander Voss checked "
            "the readout again, fingers tracing the faded numbers. Nothing "
            "had changed. The signal was still there, pulsing like a heartbeat "
            "from a dead world."
        )
        result = compute_slop_score(prose)
        assert result.slop_ratio >= 0.9
        assert result.is_clean

    def test_slop_heavy_prose_scores_low(self):
        prose = (
            "She decided to delve into the tapestry of mysteries, which was "
            "a testament to her multifaceted nature. The symphony of voices "
            "echoed through the labyrinthine corridors as she began to embark "
            "on this pivotal journey."
        )
        result = compute_slop_score(prose)
        assert result.slop_ratio < 0.9
        assert not result.is_clean
        assert result.phrase_count >= 3

    def test_empty_prose(self):
        result = compute_slop_score("")
        assert result.slop_ratio == 1.0
        assert result.total_words == 0
        assert result.is_clean

    def test_single_slop_phrase(self):
        prose = "The results were a testament to our hard work and dedication."
        result = compute_slop_score(prose)
        assert result.phrase_count >= 1
        found_lower = [p.lower() for p in result.found_phrases]
        assert any("testament to" in p for p in found_lower)

    def test_case_insensitive(self):
        prose = "She chose to DELVE into the mystery."
        result = compute_slop_score(prose)
        assert result.phrase_count >= 1

    def test_regex_pattern_matches(self):
        """The regex slop pattern 'little did X know' should match."""
        prose = "Little did she know that the world was about to change."
        result = compute_slop_score(prose)
        # Should be caught by structural regex
        assert result.phrase_count >= 1 or result.pattern_count >= 1

    def test_structural_pattern_not_x_but_y(self):
        """'Not X but Y' construction is a high-signal AI tell."""
        prose = "It was not fear but curiosity that drove her forward."
        result = compute_slop_score(prose)
        assert result.pattern_count >= 1
        assert any("not" in p.lower() for p in result.found_patterns)

    def test_structural_pattern_transition_openers(self):
        """Transition word sentence openers should be detected."""
        prose = "The rain fell. However, she pressed onward into the storm."
        result = compute_slop_score(prose)
        assert result.pattern_count >= 1

    def test_result_has_weighted_fields(self):
        """SlopResult should have phrase_count and pattern_count."""
        prose = "She delved into the mystery. However, it was not fear but wonder."
        result = compute_slop_score(prose)
        assert isinstance(result.phrase_count, int)
        assert isinstance(result.pattern_count, int)
        assert result.phrase_count + result.pattern_count > 0

    def test_weighted_scoring_penalizes_more_for_sloppy_phrases(self):
        """Phrases with higher penalty weights should lower the ratio more."""
        # "delve" has max penalty (0.96875), a single hit in short prose
        # should meaningfully affect the ratio
        short_prose = "She decided to delve into it."
        result = compute_slop_score(short_prose)
        assert result.slop_ratio < 1.0
        assert result.phrase_count == 1

    def test_is_clean_property(self):
        """is_clean should be True only when no phrases or patterns found."""
        clean = compute_slop_score("The cat sat on the mat.")
        assert clean.is_clean

        sloppy = compute_slop_score("She delved into the tapestry.")
        assert not sloppy.is_clean
