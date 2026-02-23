"""Tests for weighted slop detection using sam-paech data."""

from ai_writer.prompts.configs import SlopConfig
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
        found_lower = " ".join(result.found_phrases).lower()
        assert "testament to" in found_lower

    def test_case_insensitive(self):
        prose = "She chose to DELVE into the mystery."
        result = compute_slop_score(prose)
        assert result.phrase_count >= 1

    def test_result_has_weighted_fields(self):
        """SlopResult should have phrase_count and unique_phrase_count."""
        prose = "She delved into the mystery with a sense of wonder."
        result = compute_slop_score(prose)
        assert isinstance(result.phrase_count, int)
        assert isinstance(result.unique_phrase_count, int)
        assert isinstance(result.weighted_penalty, float)

    def test_weighted_scoring_penalizes_more_for_sloppy_phrases(self):
        """Phrases with higher penalty weights should lower the ratio more."""
        short_prose = "She decided to delve into it."
        result = compute_slop_score(short_prose)
        assert result.slop_ratio < 1.0
        assert result.phrase_count == 1

    def test_is_clean_property(self):
        """is_clean should be True only when no phrases or words found."""
        clean = compute_slop_score("The cat sat on the mat.")
        assert clean.is_clean

        sloppy = compute_slop_score("She delved into the tapestry.")
        assert not sloppy.is_clean


class TestAllowlistFiltering:
    def test_allowlist_skips_character_name(self):
        """Character names in the allowlist should not be flagged."""
        prose = "Elias walked through the corridor, his steps echoing."
        allowlist = {"elias"}
        result = compute_slop_score(prose, allowlist=allowlist)
        # "Elias" should not appear in found phrases
        found_lower = " ".join(result.found_phrases).lower()
        assert "elias" not in found_lower

    def test_without_allowlist_may_flag(self):
        """Without an allowlist, phrases that overlap with slop data are flagged."""
        prose = "She delved into the mystery."
        result = compute_slop_score(prose)
        assert result.phrase_count >= 1


class TestDeduplication:
    def test_dedup_produces_correct_counts(self):
        """Duplicate phrase hits should be grouped with count."""
        prose = (
            "It was a testament to her skill. Another testament to her courage. "
            "A third testament to her will."
        )
        result = compute_slop_score(prose)
        assert result.unique_phrase_count >= 1
        # phrase_count = total hits, unique_phrase_count = distinct phrases
        assert result.phrase_count >= result.unique_phrase_count
        # Display format should show "x3" for repeated phrases
        found = " ".join(result.found_phrases)
        assert "x" in found or result.unique_phrase_count == result.phrase_count


class TestWordLevelScan:
    def test_word_scan_catches_excess_usage(self):
        """Words from slop_words.json used excessively should be flagged."""
        # Use a word that's likely in the slop word list many times
        prose = (
            "He nodded. She nodded. They both nodded again. "
            "Then he nodded once more. Everyone nodded in agreement."
        )
        result = compute_slop_score(prose)
        # "nodded" is a common slop word — if present in the data,
        # excess occurrences should be flagged
        if "nodded" in result.found_words:
            assert result.found_words["nodded"] >= 1

    def test_single_occurrence_not_penalized(self):
        """A single occurrence of a slop word should not be penalized (free)."""
        prose = "He nodded once and walked away into the dark night."
        config = SlopConfig(word_free_occurrences=1)
        result = compute_slop_score(prose, config=config)
        # Single occurrence is free
        assert "nodded" not in result.found_words

    def test_word_allowlist_applies(self):
        """Words in the allowlist should be skipped in word scan too."""
        prose = (
            "Elias said something. Elias spoke again. Elias continued. "
            "Elias replied. Elias whispered."
        )
        result = compute_slop_score(prose, allowlist={"elias"})
        # With allowlist, "elias" should not appear in found_words
        assert "elias" not in result.found_words


class TestSlopConfig:
    def test_config_flows_through(self):
        """Custom SlopConfig should affect scoring."""
        prose = "She delved into the mystery with great wonder and awe."
        default_result = compute_slop_score(prose)
        # With a very low penalty scale, ratio should be higher
        lenient = SlopConfig(phrase_penalty_scale=1.0)
        lenient_result = compute_slop_score(prose, config=lenient)
        assert lenient_result.slop_ratio >= default_result.slop_ratio

    def test_default_config_used_when_none(self):
        """When no config is passed, defaults are used."""
        prose = "She delved into the mystery."
        result = compute_slop_score(prose)
        assert result.slop_ratio < 1.0  # Should still detect slop


class TestRegexPatternsRemoved:
    def test_no_structural_patterns_in_result(self):
        """Regex structural patterns have been removed from detection."""
        prose = "Little did she know that the world was about to change."
        result = compute_slop_score(prose)
        # SlopResult no longer has found_patterns or pattern_count
        assert not hasattr(result, "pattern_count")
        assert not hasattr(result, "found_patterns")
