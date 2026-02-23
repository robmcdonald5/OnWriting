"""Weighted slop detection using sam-paech/antislop-sampler phrase & word data.

Detects AI-characteristic patterns via:
- 517 statistically-derived phrases from antislop-sampler (weighted)
- 2000 overrepresented words from slop-forensics (excess-count penalty)
- Schema-aware allowlist to suppress false positives (character names, etc.)
- Deduplication to report unique phrases with occurrence counts
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ai_writer.prompts.configs import SlopConfig
from ai_writer.utils.slop_data import get_slop_phrases, get_slop_words

# --- Phrase Pattern Cache ---

_compiled_phrases: list[tuple[re.Pattern[str], float, str]] | None = None


def _get_compiled_phrases() -> list[tuple[re.Pattern[str], float, str]]:
    """Compile phrase patterns from vendored data (cached after first call).

    Returns list of (compiled_pattern, penalty_weight, original_phrase).
    """
    global _compiled_phrases
    if _compiled_phrases is not None:
        return _compiled_phrases

    phrases = get_slop_phrases(min_severity=0.0)
    compiled: list[tuple[re.Pattern[str], float, str]] = []
    for phrase, weight in phrases:
        stripped = phrase.strip()
        if len(stripped) < 3:
            continue
        try:
            pattern = re.compile(rf"\b{re.escape(stripped)}\b", re.IGNORECASE)
            compiled.append((pattern, weight, stripped))
        except re.error:
            continue

    _compiled_phrases = compiled
    return _compiled_phrases


@dataclass
class SlopResult:
    """Result of weighted slop phrase and word detection."""

    # Phrase-level results (deduplicated: "phrase x2 (weight: 0.97)")
    found_phrases: list[str] = field(default_factory=list)
    total_words: int = 0
    slop_ratio: float = 1.0  # 1.0 = clean, 0.0 = heavy slop
    phrase_count: int = 0  # total phrase hits (including duplicates)
    unique_phrase_count: int = 0  # distinct phrases found
    # Word-level results
    found_words: dict[str, int] = field(default_factory=dict)  # word -> excess count
    # Debugging
    weighted_penalty: float = 0.0  # raw penalty before ratio computation

    @property
    def is_clean(self) -> bool:
        return self.phrase_count == 0 and not self.found_words


def compute_slop_score(
    prose: str,
    allowlist: set[str] | None = None,
    config: SlopConfig | None = None,
) -> SlopResult:
    """Scan prose for overused LLM phrases and overrepresented words.

    Uses weighted scoring from sam-paech antislop-sampler data:
    - Each phrase hit contributes its penalty weight (higher = more sloppy)
    - Each excess word occurrence contributes word_excess_weight * word_weight
    - Final ratio: ``1 - (weighted_penalty / total_words) * scale``, clamped [0, 1]

    Args:
        prose: Text to scan.
        allowlist: Lowercased terms to skip (character names, locations, etc.).
        config: Scoring configuration. Uses defaults if None.
    """
    if config is None:
        config = SlopConfig()
    if allowlist is None:
        allowlist = set()

    words = prose.split()
    total_words = len(words)
    if total_words == 0:
        return SlopResult()

    # --- Phrase matching (weighted, with allowlist and dedup) ---
    # Collect all raw matches first
    raw_matches: list[tuple[str, float]] = []  # (matched_text, weight)

    for pattern, weight, _original in _get_compiled_phrases():
        matches = pattern.findall(prose)
        for match_text in matches:
            if match_text.lower() in allowlist:
                continue
            raw_matches.append((match_text, weight))

    # Deduplicate: group by lowercased text, track count and max weight
    phrase_groups: dict[str, tuple[int, float, str]] = {}
    for match_text, weight in raw_matches:
        key = match_text.lower()
        if key in phrase_groups:
            count, max_w, example = phrase_groups[key]
            phrase_groups[key] = (count + 1, max(max_w, weight), example)
        else:
            phrase_groups[key] = (1, weight, match_text)

    # Build display list and compute phrase penalty
    found_phrases: list[str] = []
    phrase_penalty = 0.0
    total_phrase_hits = 0

    for _key, (count, max_weight, example) in sorted(
        phrase_groups.items(), key=lambda x: x[1][1], reverse=True
    ):
        if count > 1:
            found_phrases.append(f'"{example}" x{count} (weight: {max_weight:.2f})')
        else:
            found_phrases.append(f'"{example}" (weight: {max_weight:.2f})')
        phrase_penalty += count * max_weight
        total_phrase_hits += count

    # --- Word-level scan (excess occurrences) ---
    found_words: dict[str, int] = {}
    word_penalty = 0.0

    slop_words = get_slop_words(min_severity=config.word_min_severity)
    if slop_words:
        # Count all words in prose (lowercased)
        prose_word_counts: dict[str, int] = {}
        for w in words:
            w_lower = w.lower().strip(".,!?;:\"'()-")
            if w_lower:
                prose_word_counts[w_lower] = prose_word_counts.get(w_lower, 0) + 1

        for slop_word, slop_weight in slop_words:
            if slop_word.lower() in allowlist:
                continue
            count = prose_word_counts.get(slop_word.lower(), 0)
            excess = count - config.word_free_occurrences
            if excess > 0:
                found_words[slop_word] = excess
                word_penalty += excess * config.word_excess_weight * slop_weight

    weighted_penalty = phrase_penalty + word_penalty

    # Weighted ratio: higher penalty = lower ratio
    ratio = max(
        0.0, 1.0 - (weighted_penalty / total_words) * config.phrase_penalty_scale
    )

    return SlopResult(
        found_phrases=found_phrases,
        total_words=total_words,
        slop_ratio=round(ratio, 2),
        phrase_count=total_phrase_hits,
        unique_phrase_count=len(phrase_groups),
        found_words=found_words,
        weighted_penalty=round(weighted_penalty, 3),
    )
