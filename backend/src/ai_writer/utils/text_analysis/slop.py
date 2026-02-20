"""Weighted slop detection using sam-paech/antislop-sampler phrase data.

Replaces the original flat list of 55 hand-picked literals with:
- 517 statistically-derived phrases from antislop-sampler (weighted)
- Structural regex patterns for high-signal AI constructions
- Weighted scoring that penalizes distinctive AI-isms more heavily
"""

import re
from dataclasses import dataclass, field

from ai_writer.utils.slop_data import get_slop_phrases

# --- Structural Regex Patterns ---

# These catch structural AI tells beyond individual phrases.
_SLOP_REGEX: list[str] = [
    r"little did .{1,20} know",
    r"(?i)not [^.!?]{3,60} but",  # "not X but Y" construction
    r"(?:^|\.\s+)(?:However|Moreover|Furthermore|Additionally),",  # transition openers
    r"(?:—|--).{3,50}(?:—|--)",  # excessive em-dash parentheticals
]

_STRUCTURAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(pattern, re.IGNORECASE | re.MULTILINE) for pattern in _SLOP_REGEX
]

# --- Phrase Pattern Cache ---

_compiled_phrases: list[tuple[re.Pattern[str], float]] | None = None


def _get_compiled_phrases() -> list[tuple[re.Pattern[str], float]]:
    """Compile phrase patterns from vendored data (cached after first call)."""
    global _compiled_phrases
    if _compiled_phrases is not None:
        return _compiled_phrases

    phrases = get_slop_phrases(min_severity=0.0)
    compiled: list[tuple[re.Pattern[str], float]] = []
    for phrase, weight in phrases:
        # Skip very short phrases that would cause noisy matches
        if len(phrase.strip()) < 3:
            continue
        try:
            pattern = re.compile(rf"\b{re.escape(phrase.strip())}\b", re.IGNORECASE)
            compiled.append((pattern, weight))
        except re.error:
            # Skip phrases that can't be compiled as regex
            continue

    _compiled_phrases = compiled
    return _compiled_phrases


@dataclass
class SlopResult:
    """Result of weighted slop phrase detection."""

    found_phrases: list[str] = field(default_factory=list)
    found_patterns: list[str] = field(default_factory=list)
    total_words: int = 0
    slop_ratio: float = 1.0  # 1.0 = clean, 0.0 = heavy slop
    phrase_count: int = 0  # raw phrase hits
    pattern_count: int = 0  # raw structural pattern hits

    @property
    def is_clean(self) -> bool:
        return self.phrase_count == 0 and self.pattern_count == 0


def compute_slop_score(prose: str) -> SlopResult:
    """Scan prose for overused LLM phrases and structural patterns.

    Uses weighted scoring from sam-paech antislop-sampler data:
    - Each phrase hit contributes its penalty weight (higher = more sloppy)
    - Structural regex patterns contribute a fixed penalty of 0.5 each
    - Final ratio: ``1 - (weighted_penalty / total_words) * 10``, clamped [0, 1]

    For a 1000-word passage, ~10 weighted penalty points → ratio ~0.9.
    Heavy slop (30+ penalty points) floors the ratio at 0.0.
    """
    words = prose.split()
    total_words = len(words)
    if total_words == 0:
        return SlopResult()

    # --- Phrase matching (weighted) ---
    found_phrases: list[str] = []
    weighted_penalty = 0.0

    for pattern, weight in _get_compiled_phrases():
        matches = pattern.findall(prose)
        if matches:
            found_phrases.extend(matches)
            weighted_penalty += len(matches) * weight

    # --- Structural pattern matching (fixed weight per hit) ---
    found_patterns: list[str] = []
    structural_weight = 0.5  # fixed penalty per structural match

    for pattern in _STRUCTURAL_PATTERNS:
        matches = pattern.findall(prose)
        if matches:
            found_patterns.extend(matches)
            weighted_penalty += len(matches) * structural_weight

    phrase_count = len(found_phrases)
    pattern_count = len(found_patterns)

    # Weighted ratio: higher penalty = lower ratio
    ratio = max(0.0, 1.0 - (weighted_penalty / total_words) * 10)

    return SlopResult(
        found_phrases=found_phrases,
        found_patterns=found_patterns,
        total_words=total_words,
        slop_ratio=round(ratio, 2),
        phrase_count=phrase_count,
        pattern_count=pattern_count,
    )
