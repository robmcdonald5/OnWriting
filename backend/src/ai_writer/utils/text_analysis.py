"""Deterministic text analysis utilities — zero LLM cost.

These run before the Style Editor LLM call to catch objective issues
that don't need subjective judgment: word count deviations, tense
inconsistencies, and overused LLM phrases ("slop").
"""

import re
from dataclasses import dataclass, field

# --- Slop Detection ---

# Common LLM-isms sourced from EQ-Bench "slop score" and community lists.
# Literal phrases are escaped for safe regex compilation.
_SLOP_LITERALS: list[str] = [
    "delve",
    "tapestry",
    "testament to",
    "it's worth noting",
    "it is worth noting",
    "myriad",
    "embark",
    "navigate the",
    "multifaceted",
    "pivotal",
    "in the realm of",
    "a symphony of",
    "a dance of",
    "nestled",
    "the silence was deafening",
    "sent shivers down",
    "a weight settled",
    "eyes widened",
    "heart pounded",
    "breath caught",
    "shattered the silence",
    "hung heavy in the air",
    "cutting through the",
    "echoed through",
    "loomed large",
    "gossamer",
    "iridescent",
    "luminous",
    "resplendent",
    "enigmatic",
    "cacophony",
    "serendipitous",
    "ineffable",
    "palpable tension",
    "couldn't help but",
    "a sense of",
    "in that moment",
    "the world seemed to",
    "time seemed to",
]

# Regex patterns for slop phrases that need flexible matching.
# These are compiled as-is (NOT escaped).
_SLOP_REGEX: list[str] = [
    r"little did .{1,20} know",
]

# Pre-compile all patterns for performance
_SLOP_PATTERNS: list[re.Pattern[str]] = [
    re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE) for phrase in _SLOP_LITERALS
] + [re.compile(rf"\b{pattern}\b", re.IGNORECASE) for pattern in _SLOP_REGEX]


@dataclass
class SlopResult:
    """Result of slop phrase detection."""

    found_phrases: list[str] = field(default_factory=list)
    total_words: int = 0
    slop_ratio: float = 1.0  # 1.0 = clean, 0.0 = heavy slop

    @property
    def is_clean(self) -> bool:
        return len(self.found_phrases) == 0


def compute_slop_score(prose: str) -> SlopResult:
    """Scan prose for overused LLM phrases and return a cleanliness ratio.

    The ratio uses a ×10 penalty multiplier to make slop visible even in
    long texts: ``1 - (slop_hits / total_words) * 10``, clamped to [0, 1].
    For a 1000-word passage, 10 slop hits produce a ratio of 0.9;
    100 hits would floor it at 0.0.
    """
    words = prose.split()
    total_words = len(words)
    if total_words == 0:
        return SlopResult(found_phrases=[], total_words=0, slop_ratio=1.0)

    found: list[str] = []
    for pattern in _SLOP_PATTERNS:
        matches = pattern.findall(prose)
        found.extend(matches)

    hit_count = len(found)
    ratio = max(0.0, 1.0 - (hit_count / total_words) * 10)

    return SlopResult(
        found_phrases=found,
        total_words=total_words,
        slop_ratio=round(ratio, 2),
    )


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
