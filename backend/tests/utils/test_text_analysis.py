"""Tests for deterministic text analysis utilities."""

from unittest.mock import patch

from ai_writer.utils.text_analysis import (
    check_tense_consistency,
    check_word_count,
    compute_slop_score,
)


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
            "a testament to her multifaceted nature. It's worth noting that "
            "she chose to embark on this pivotal journey to navigate the "
            "enigmatic realm of the unknown."
        )
        result = compute_slop_score(prose)
        assert result.slop_ratio < 0.9
        assert not result.is_clean
        assert len(result.found_phrases) >= 5

    def test_empty_prose(self):
        result = compute_slop_score("")
        assert result.slop_ratio == 1.0
        assert result.total_words == 0
        assert result.is_clean

    def test_single_slop_phrase(self):
        prose = "The results were a testament to our hard work and dedication."
        result = compute_slop_score(prose)
        assert len(result.found_phrases) == 1
        assert "testament to" in result.found_phrases[0].lower()

    def test_case_insensitive(self):
        prose = "She chose to DELVE into the mystery."
        result = compute_slop_score(prose)
        assert len(result.found_phrases) >= 1

    def test_regex_pattern_matches(self):
        """The regex slop pattern 'little did X know' should match."""
        prose = "Little did she know that the world was about to change."
        result = compute_slop_score(prose)
        assert len(result.found_phrases) >= 1
        assert "little did she know" in result.found_phrases[0].lower()


class TestCheckWordCount:
    def test_within_tolerance(self):
        prose = " ".join(["word"] * 900)
        result = check_word_count(prose, target=1000, tolerance=0.25)
        assert result.within_tolerance is True
        assert result.actual == 900

    def test_over_tolerance(self):
        prose = " ".join(["word"] * 1500)
        result = check_word_count(prose, target=1000, tolerance=0.25)
        assert result.within_tolerance is False
        assert result.deviation > 0.25

    def test_under_tolerance(self):
        prose = " ".join(["word"] * 500)
        result = check_word_count(prose, target=1000, tolerance=0.25)
        assert result.within_tolerance is False
        assert result.deviation < -0.25

    def test_exact_match(self):
        prose = " ".join(["word"] * 1000)
        result = check_word_count(prose, target=1000)
        assert result.within_tolerance is True
        assert result.deviation == 0.0

    def test_zero_target(self):
        prose = "Some words here."
        result = check_word_count(prose, target=0)
        assert result.within_tolerance is True

    def test_edge_of_tolerance(self):
        # 25% over 1000 = 1250
        prose = " ".join(["word"] * 1250)
        result = check_word_count(prose, target=1000, tolerance=0.25)
        assert result.within_tolerance is True


class TestCheckTenseConsistency:
    def test_consistent_past_tense(self):
        prose = (
            "She walked down the empty corridor. The lights flickered "
            "overhead as she reached the control room. She had been "
            "waiting for hours. The door opened with a hiss."
        )
        result = check_tense_consistency(prose)
        assert result.dominant_tense == "past"
        assert result.consistent is True
        assert result.minority_ratio < 0.15

    def test_consistent_present_tense(self):
        prose = (
            "She walks down the empty corridor. The lights flicker "
            "overhead as she reaches the control room. The door opens "
            "with a hiss. She steps inside."
        )
        result = check_tense_consistency(prose)
        assert result.dominant_tense == "present"
        assert result.consistent is True

    def test_inconsistent_mixed_tense(self):
        prose = (
            "She walked down the corridor yesterday. Now she walks back "
            "the same way. The door opened but she opens it again. "
            "He ran fast but he runs even faster now. They talked but "
            "they also talk to others. She looked around and she looks again."
        )
        result = check_tense_consistency(prose)
        assert result.past_ratio > 0.0
        assert result.present_ratio > 0.0
        assert result.consistent is False

    def test_dialogue_stripped_before_analysis(self):
        """Past-tense narration with present-tense dialogue should be consistent."""
        prose = (
            'She walked down the corridor. "I know what this means," she said. '
            'The lights flickered overhead. "It looks like we have a problem," '
            "he muttered. She reached for the controls and pulled the lever."
        )
        result = check_tense_consistency(prose)
        assert result.dominant_tense == "past"
        assert result.consistent is True

    def test_smart_quotes_stripped(self):
        """Curly/smart quotes should also be stripped before analysis."""
        prose = (
            "She walked down the corridor. "
            "\u201cI know what this means,\u201d she said. "
            "The lights flickered overhead. "
            "\u201cIt looks like we have a problem,\u201d he muttered. "
            "She reached for the controls and pulled the lever."
        )
        result = check_tense_consistency(prose)
        assert result.dominant_tense == "past"
        assert result.consistent is True

    def test_empty_prose(self):
        result = check_tense_consistency("")
        assert result.dominant_tense == "unknown"
        assert result.consistent is True

    def test_spacy_model_missing_returns_unknown(self):
        """When spaCy model is not installed, return unknown/consistent."""
        import ai_writer.utils.text_analysis as module

        # Reset cached model so _get_nlp() tries to load again
        original = module._nlp_model
        module._nlp_model = None
        try:
            with patch.object(module, "_get_nlp", return_value=None):
                result = check_tense_consistency("She walked down the hall.")
                assert result.dominant_tense == "unknown"
                assert result.consistent is True
        finally:
            module._nlp_model = original
