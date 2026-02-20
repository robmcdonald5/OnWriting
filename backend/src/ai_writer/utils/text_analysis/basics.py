"""Basic deterministic text checks — word count and tense consistency.

These run before the Style Editor LLM call to catch objective issues
that don't need subjective judgment.
"""

import re
from dataclasses import dataclass

# --- Word Count Check ---


@dataclass
class WordCountResult:
    """Result of word count tolerance check."""

    actual: int = 0
    target: int = 0
    within_tolerance: bool = True
    deviation: float = 0.0  # percentage deviation, e.g. 0.15 = 15% over


def check_word_count(
    prose: str, target: int, tolerance: float = 0.25
) -> WordCountResult:
    """Compare actual word count against target within tolerance.

    Args:
        prose: The text to count.
        target: Target word count from SceneOutline (must be > 0).
        tolerance: Acceptable deviation as a fraction (0.25 = +/- 25%).

    Returns:
        WordCountResult with actual count, target, deviation, and pass/fail.
    """
    actual = len(prose.split())
    if target <= 0:
        return WordCountResult(actual=actual, target=target, within_tolerance=True)

    deviation = (actual - target) / target
    within = abs(deviation) <= tolerance

    return WordCountResult(
        actual=actual,
        target=target,
        within_tolerance=within,
        deviation=round(deviation, 3),
    )


# --- Tense Consistency Check ---

# Lazy-cached spaCy model — loaded once on first use, not per call.
_nlp_model = None


def _get_nlp():
    """Load and cache the spaCy model. Returns None if model is not installed."""
    global _nlp_model
    if _nlp_model is None:
        import spacy

        try:
            _nlp_model = spacy.load("en_core_web_sm")
        except OSError:
            # Model not installed — return None, callers handle gracefully
            return None
    return _nlp_model


@dataclass
class TenseResult:
    """Result of tense consistency analysis."""

    dominant_tense: str = "unknown"  # "past", "present", or "unknown"
    past_ratio: float = 0.0
    present_ratio: float = 0.0
    consistent: bool = True
    minority_ratio: float = 0.0  # ratio of the non-dominant tense


def _strip_dialogue(prose: str) -> str:
    """Remove quoted dialogue so tense analysis only covers narration.

    Handles straight double quotes, curly/smart double quotes, and
    single quotes used as dialogue markers (capital letter after opening quote).
    """
    # Straight double quotes
    stripped = re.sub(r'"[^"]*"', "", prose)
    # Curly/smart double quotes (U+201C / U+201D)
    stripped = re.sub(r"\u201c[^\u201d]*\u201d", "", stripped)
    # Single-quoted dialogue (full sentences only — avoids contractions)
    # Matches: 'Hello,' she said  but not: she's, don't, it's
    stripped = re.sub(r"'[A-Z][^']*'", "", stripped)
    # Curly/smart single quotes (U+2018 / U+2019) — dialogue only
    stripped = re.sub(r"\u2018[A-Z][^\u2019]*\u2019", "", stripped)
    return stripped


def check_tense_consistency(prose: str, threshold: float = 0.15) -> TenseResult:
    """Detect tense distribution using spaCy POS tags on narration only.

    Strips quoted dialogue before analysis, since dialogue legitimately
    uses present tense even in past-tense narratives.

    Uses fine-grained POS tags:
    - VBD (past tense), VBN (past participle) → past
    - VBP (non-3rd-sg present), VBZ (3rd-sg present) → present

    Args:
        prose: The text to analyze.
        threshold: Maximum acceptable minority tense ratio (default 15%).

    Returns:
        TenseResult with dominant tense, ratios, and consistency flag.
    """
    nlp = _get_nlp()
    if nlp is None:
        return TenseResult(dominant_tense="unknown", consistent=True)

    narration = _strip_dialogue(prose)
    doc = nlp(narration)

    past_tags = {"VBD", "VBN"}
    present_tags = {"VBP", "VBZ"}

    past_count = 0
    present_count = 0

    for token in doc:
        if token.tag_ in past_tags:
            past_count += 1
        elif token.tag_ in present_tags:
            present_count += 1

    total = past_count + present_count
    if total == 0:
        return TenseResult(dominant_tense="unknown", consistent=True)

    past_ratio = past_count / total
    present_ratio = present_count / total

    if past_ratio >= present_ratio:
        dominant = "past"
        minority = present_ratio
    else:
        dominant = "present"
        minority = past_ratio

    return TenseResult(
        dominant_tense=dominant,
        past_ratio=round(past_ratio, 3),
        present_ratio=round(present_ratio, 3),
        consistent=minority <= threshold,
        minority_ratio=round(minority, 3),
    )
