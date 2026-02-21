"""Tests for cross-scene repetition detection."""

from ai_writer.utils.text_analysis import detect_cross_scene_repetition


class TestDetectCrossSceneRepetition:
    def test_catches_verbatim_repetition(self):
        current = (
            "The anomaly pulsed with an eerie luminescence that defied explanation."
        )
        prior = ["She studied the anomaly pulsed with an eerie luminescence carefully."]
        result = detect_cross_scene_repetition(current, prior)
        assert result.repeated_count > 0
        # The shared n-gram should be found
        assert any(
            "anomaly pulsed with" in phrase for phrase in result.repeated_phrases
        )

    def test_no_repetition_returns_empty(self):
        current = "The stars burned cold and distant above the station."
        prior = ["She walked through the garden, smelling the roses."]
        result = detect_cross_scene_repetition(current, prior)
        assert result.repeated_count == 0
        assert result.repeated_phrases == []

    def test_single_scene_no_prior(self):
        """First scene has no prior scenes — should return empty."""
        current = "The engineer checked the console readings."
        result = detect_cross_scene_repetition(current, [])
        assert result.repeated_count == 0

    def test_empty_current_prose(self):
        result = detect_cross_scene_repetition("", ["Some prior scene text here."])
        assert result.repeated_count == 0

    def test_filters_common_collocations(self):
        """Very common word sequences should be filtered out."""
        # "she said as she" — all very common words
        current = "Then she said as she walked down the corridor."
        prior = ["Earlier she said as she left the room in a hurry."]
        result = detect_cross_scene_repetition(current, prior)
        # Common collocations should be filtered
        assert not any(
            "she said as she" in phrase for phrase in result.repeated_phrases
        )

    def test_multiple_prior_scenes(self):
        """Detects repetition across any prior scene, not just the last one."""
        current = "The crystalline structures hummed with dormant energy."
        prior_scenes = [
            "She examined the crystalline structures hummed with dormant power.",
            "A completely different scene about something else entirely here.",
        ]
        result = detect_cross_scene_repetition(current, prior_scenes)
        assert result.repeated_count > 0

    def test_deduplicates_substrings(self):
        """Longer n-gram subsumes shorter overlapping n-grams."""
        current = "the ancient beacon flickered with an amber glow in the darkness"
        prior = ["the ancient beacon flickered with an amber glow was beautiful"]
        result = detect_cross_scene_repetition(current, prior)
        # Should find the long phrase, not also report shorter substrings
        phrases = result.repeated_phrases
        for i, p1 in enumerate(phrases):
            for j, p2 in enumerate(phrases):
                if i != j:
                    assert p1 not in p2, f"'{p1}' is a substring of '{p2}'"
