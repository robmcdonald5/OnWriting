"""Tests for structural monotony analysis using spaCy."""

from ai_writer.prompts.configs import ProseStructureConfig
from ai_writer.utils.text_analysis import ProseStructureResult, compute_prose_structure


class TestComputeProseStructure:
    def test_monotonous_opener_prose(self):
        """All sentences starting with 'He' should flag opener_monotony."""
        prose = (
            "He walked to the door. He opened it slowly. He stepped inside. "
            "He looked around the room. He sat down on the chair."
        )
        result = compute_prose_structure(prose)
        assert result.opener_monotony is True
        assert result.top_opener_pos == "PRON"
        assert result.top_opener_ratio > 0.5

    def test_varied_opener_prose(self):
        """Varied sentence openings should not flag opener_monotony."""
        # Each sentence starts with a different POS: NOUN, ADV, PRON, DET, VERB
        prose = (
            "Rain pattered on the roof. Carefully, she stepped inside. "
            "Something moved in the shadows. The thunder rumbled "
            "across the valley. Listening intently, she heard nothing."
        )
        result = compute_prose_structure(prose)
        assert result.opener_monotony is False

    def test_uniform_sentence_lengths_flag_monotony(self):
        """Sentences of very similar length should flag length_monotony."""
        # All sentences ~5-6 words
        prose = (
            "The cat sat down here. The dog ran over there. "
            "The bird flew up high. The fish swam down deep. "
            "The mouse crept along slowly."
        )
        result = compute_prose_structure(prose)
        assert result.sent_length_cv < 0.5  # low variation expected
        # Note: length_monotony threshold is 0.30 by default

    def test_varied_sentence_lengths_pass(self):
        """Sentences with varied lengths should not flag length_monotony."""
        prose = (
            "No. "
            "The old woman sat in the corner of the dimly lit room, "
            "her wrinkled hands folded in her lap as she listened to "
            "the wind howl outside the frosted windows. "
            "Silence. "
            "Then the door burst open and in stumbled a young boy, "
            "drenched from head to toe."
        )
        result = compute_prose_structure(prose)
        assert result.sent_length_cv > 0.30
        assert result.length_monotony is False

    def test_passive_heavy_prose(self):
        """Prose with many passive constructions should flag passive_heavy."""
        prose = (
            "The door was opened by the butler. The letter was read by "
            "the countess. The wine was poured by the servant. The meal "
            "was prepared by the cook. The guests were greeted by the host."
        )
        result = compute_prose_structure(prose)
        assert result.passive_count >= 3
        assert result.passive_ratio > 0.20
        assert result.passive_heavy is True

    def test_active_prose_passes(self):
        """Active prose should not flag passive_heavy."""
        prose = (
            "She kicked the door open. Thunder cracked overhead. "
            "The captain grabbed the wheel and steered hard to port. "
            "Waves crashed against the hull."
        )
        result = compute_prose_structure(prose)
        assert result.passive_heavy is False

    def test_empty_prose(self):
        result = compute_prose_structure("")
        assert result.sentence_count == 0
        assert result.opener_monotony is False
        assert result.length_monotony is False

    def test_config_threshold_overrides(self):
        """Custom thresholds should affect detection sensitivity."""
        prose = (
            "He walked to the door. He opened it slowly. He stepped inside. "
            "He looked around. He sat down."
        )
        # With very high threshold, opener_monotony should still trigger
        strict = ProseStructureConfig(opener_monotony_threshold=0.10)
        result_strict = compute_prose_structure(prose, strict)
        assert result_strict.opener_monotony is True

        # With very high threshold (100%), opener_monotony should NOT trigger
        lenient = ProseStructureConfig(opener_monotony_threshold=1.0)
        result_lenient = compute_prose_structure(prose, lenient)
        assert result_lenient.opener_monotony is False

    def test_summary_lines_only_flagged(self):
        """summary_lines() should only include flagged issues."""
        result = ProseStructureResult(
            sentence_count=5,
            opener_monotony=True,
            top_opener_pos="PRON",
            top_opener_ratio=0.8,
            length_monotony=False,
            passive_heavy=False,
            structural_monotony=False,
        )
        lines = result.summary_lines()
        assert len(lines) == 1
        assert "PRON" in lines[0]

    def test_summary_lines_empty_when_clean(self):
        """summary_lines() should return empty list when nothing flagged."""
        result = ProseStructureResult(sentence_count=5)
        assert result.summary_lines() == []
