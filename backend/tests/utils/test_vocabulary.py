"""Tests for vocabulary diversity, sophistication, and readability metrics."""

from ai_writer.prompts.configs import VocabularyConfig
from ai_writer.utils.text_analysis import VocabularyResult, compute_vocabulary_metrics


class TestComputeVocabularyMetrics:
    def test_repetitive_vocabulary_flags_low_diversity(self):
        """Prose with very repetitive words should have low MTLD."""
        # Deliberately repetitive vocabulary
        prose = (
            "The man walked to the door. The man opened the door. "
            "The man went through the door. The man closed the door. "
            "The man stood by the door. The man looked at the door."
        )
        result = compute_vocabulary_metrics(prose)
        assert result.low_diversity is True
        assert result.mtld < 60.0

    def test_rich_vocabulary_passes(self):
        """Prose with diverse vocabulary should pass diversity check."""
        prose = (
            "Crimson twilight cascaded across the jagged mountain peaks "
            "as thunderous waterfalls plummeted into obsidian ravines below. "
            "Ancient sequoias whispered forgotten melodies while phosphorescent "
            "mushrooms illuminated meandering pathways through the primordial "
            "undergrowth. Crystalline streams navigated serpentine channels "
            "carved through millennia of persistent geological transformation."
        )
        result = compute_vocabulary_metrics(prose)
        assert result.mtld > 30.0  # should be reasonably diverse

    def test_common_word_prose_flags_vocabulary_basic(self):
        """Prose using only very common words should flag vocabulary_basic."""
        prose = (
            "He said that he would go to the place and do the thing. "
            "She said that she would also go to the same place and do "
            "the same thing. They said they would all go together and "
            "do the thing they said they would do at the place."
        )
        result = compute_vocabulary_metrics(prose)
        # This prose uses extremely common words
        assert result.avg_zipf_frequency > 0

    def test_short_prose_returns_defaults(self):
        """Prose shorter than 10 words should return empty defaults."""
        result = compute_vocabulary_metrics("Too short.")
        assert result.mtld == 0.0
        assert result.low_diversity is False

    def test_config_threshold_overrides(self):
        """Custom thresholds should affect detection sensitivity."""
        prose = (
            "The man walked to the door. The man opened the door. "
            "The man went through the door. The man closed the door. "
            "The man stood by the door. The man looked at the door."
        )
        # Very lenient threshold — should not flag
        lenient = VocabularyConfig(mtld_threshold=1.0)
        result = compute_vocabulary_metrics(prose, lenient)
        assert result.low_diversity is False

        # Very strict threshold — should flag
        strict = VocabularyConfig(mtld_threshold=200.0)
        result = compute_vocabulary_metrics(prose, strict)
        assert result.low_diversity is True

    def test_readability_scores_present(self):
        """Flesch and Gunning-Fog scores should be populated."""
        prose = (
            "The quick brown fox jumped over the lazy dog. "
            "A small bird flew across the wide open field. "
            "The sun shone brightly on the green grass below."
        )
        result = compute_vocabulary_metrics(prose)
        assert result.flesch_reading_ease != 0.0
        assert result.gunning_fog != 0.0

    def test_summary_lines_only_flagged(self):
        """summary_lines() should only include flagged issues."""
        result = VocabularyResult(
            mtld=30.0,
            low_diversity=True,
            avg_zipf_frequency=4.0,
            vocabulary_basic=False,
        )
        lines = result.summary_lines()
        assert len(lines) == 1
        assert "MTLD" in lines[0]

    def test_summary_lines_empty_when_clean(self):
        """summary_lines() should return empty list when nothing flagged."""
        result = VocabularyResult()
        assert result.summary_lines() == []
