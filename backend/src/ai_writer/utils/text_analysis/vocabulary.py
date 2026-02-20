"""Vocabulary diversity, sophistication, and readability analysis.

Uses three lightweight pure-Python libraries:
- lexicalrichness: MTLD and MATTR for vocabulary diversity
- wordfreq: Zipf frequency for vocabulary sophistication
- textstat: Readability formulas (Flesch, Gunning-Fog)
"""

from dataclasses import dataclass

from ai_writer.prompts.configs import VocabularyConfig


@dataclass
class VocabularyResult:
    """Vocabulary diversity and sophistication metrics."""

    # Lexical diversity (lexicalrichness)
    mtld: float = 0.0  # Measure of Textual Lexical Diversity
    mattr: float = 0.0  # Moving Average TTR (window=50)
    low_diversity: bool = False  # True if MTLD < threshold
    # Vocabulary sophistication (wordfreq)
    avg_zipf_frequency: float = 0.0  # avg Zipf score of content words
    vocabulary_basic: bool = False  # True if avg_zipf > threshold
    # Readability (textstat)
    flesch_reading_ease: float = 0.0
    gunning_fog: float = 0.0

    def summary_lines(self) -> list[str]:
        """Return human-readable summary lines for flagged issues only."""
        lines: list[str] = []
        if self.low_diversity:
            lines.append(f"Lexical diversity MTLD: {self.mtld:.1f} — low variety")
        if self.vocabulary_basic:
            lines.append(
                f"Avg Zipf frequency: {self.avg_zipf_frequency:.2f} — "
                "overly common vocabulary"
            )
        return lines


def compute_vocabulary_metrics(
    prose: str,
    config: VocabularyConfig | None = None,
) -> VocabularyResult:
    """Analyze vocabulary diversity, sophistication, and readability.

    Args:
        prose: The text to analyze (minimum ~50 words for meaningful results).
        config: Threshold configuration. Uses defaults if None.

    Returns:
        VocabularyResult with all metrics and boolean flags.
    """
    if config is None:
        config = VocabularyConfig()

    words = prose.split()
    if len(words) < 10:
        return VocabularyResult()

    # --- Lexical diversity (lexicalrichness) ---
    from lexicalrichness import LexicalRichness  # type: ignore[import-untyped]

    lex = LexicalRichness(prose)

    try:
        mtld = lex.mtld(threshold=0.72)
    except ZeroDivisionError:
        mtld = 0.0

    try:
        mattr = lex.mattr(window_size=min(config.mattr_window, len(words)))
    except ZeroDivisionError:
        mattr = 0.0

    # --- Vocabulary sophistication (wordfreq) ---
    from wordfreq import zipf_frequency  # type: ignore[import-untyped]

    # Only score content words (skip short function words)
    content_words = [w.lower() for w in words if len(w) > 3 and w.isalpha()]
    if content_words:
        zipf_scores = [zipf_frequency(w, "en") for w in content_words]
        avg_zipf = sum(zipf_scores) / len(zipf_scores)
    else:
        avg_zipf = 0.0

    # --- Readability (textstat) ---
    from textstat import textstat as ts  # type: ignore[import-untyped]

    flesch = ts.flesch_reading_ease(prose)
    fog = ts.gunning_fog(prose)

    return VocabularyResult(
        mtld=round(mtld, 1),
        mattr=round(mattr, 3),
        low_diversity=mtld < config.mtld_threshold,
        avg_zipf_frequency=round(avg_zipf, 2),
        vocabulary_basic=avg_zipf > config.zipf_threshold,
        flesch_reading_ease=round(flesch, 1),
        gunning_fog=round(fog, 1),
    )
