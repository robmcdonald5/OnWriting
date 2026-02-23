"""Tests for basic text analysis utilities (word count, tense).

Slop detection tests have been moved to test_slop.py.
Structural analysis tests are in test_prose_structure.py.
Vocabulary tests are in test_vocabulary.py.
"""

from unittest.mock import patch

from ai_writer.utils.text_analysis import (
    check_tense_consistency,
    check_word_count,
)


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
        import ai_writer.utils.text_analysis.basics as basics_module

        # Reset cached model so _get_nlp() tries to load again
        original = basics_module._nlp_model
        basics_module._nlp_model = None
        try:
            with patch.object(basics_module, "_get_nlp", return_value=None):
                result = check_tense_consistency("She walked down the hall.")
                assert result.dominant_tense == "unknown"
                assert result.consistent is True
        finally:
            basics_module._nlp_model = original
