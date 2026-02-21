"""Cross-scene repetition detection.

Finds multi-word phrases (n-grams) that appear verbatim in both the current
scene and any prior scene. Filters out common collocations using Zipf frequency
to avoid flagging ordinary phrases like "she said as she".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wordfreq import zipf_frequency  # type: ignore[import-untyped]

try:
    from wordfreq import zipf_frequency  # type: ignore[import-untyped]

    _HAS_WORDFREQ = True
except ImportError:
    _HAS_WORDFREQ = False


@dataclass
class CrossSceneRepetitionResult:
    """Result of cross-scene repetition analysis."""

    repeated_phrases: list[str] = field(default_factory=list)
    repeated_count: int = 0


def _extract_ngrams(text: str, min_n: int, max_n: int) -> set[str]:
    """Extract normalized n-grams from text."""
    words = text.lower().split()
    # Strip leading/trailing punctuation from each word
    words = [w.strip(".,!?;:\"'()-\u2014\u2013") for w in words]
    words = [w for w in words if w]

    ngrams: set[str] = set()
    for n in range(min_n, max_n + 1):
        for i in range(len(words) - n + 1):
            ngram = " ".join(words[i : i + n])
            ngrams.add(ngram)
    return ngrams


def _is_common_collocation(ngram: str) -> bool:
    """Check if all words in the n-gram are very common (high Zipf frequency).

    Common collocations like "he turned to look at" are not notable repetitions.
    We only flag n-grams where at least one word is distinctive (Zipf <= 5.0).
    """
    if not _HAS_WORDFREQ:
        return False

    words = ngram.split()
    return all(zipf_frequency(w, "en") > 5.0 for w in words)


def detect_cross_scene_repetition(
    current_prose: str,
    prior_scene_proses: list[str],
    min_ngram: int = 4,
    max_ngram: int = 7,
) -> CrossSceneRepetitionResult:
    """Detect verbatim multi-word phrases repeated across scenes.

    Args:
        current_prose: The current scene's prose text.
        prior_scene_proses: List of prose texts from all prior scenes.
        min_ngram: Minimum n-gram size (words).
        max_ngram: Maximum n-gram size (words).

    Returns:
        CrossSceneRepetitionResult with list of repeated phrases and count.
    """
    if not prior_scene_proses or not current_prose.strip():
        return CrossSceneRepetitionResult()

    current_ngrams = _extract_ngrams(current_prose, min_ngram, max_ngram)

    # Build combined n-gram set from all prior scenes
    prior_ngrams: set[str] = set()
    for prior_prose in prior_scene_proses:
        if prior_prose.strip():
            prior_ngrams.update(_extract_ngrams(prior_prose, min_ngram, max_ngram))

    # Find intersection
    shared = current_ngrams & prior_ngrams

    # Filter out common collocations
    repeated = [ng for ng in sorted(shared) if not _is_common_collocation(ng)]

    # Remove substrings: if "fascinating no impossible" is found, don't also
    # report "fascinating no" (shorter n-gram contained in longer one)
    deduplicated: list[str] = []
    for phrase in sorted(repeated, key=len, reverse=True):
        if not any(phrase in longer for longer in deduplicated):
            deduplicated.append(phrase)

    return CrossSceneRepetitionResult(
        repeated_phrases=deduplicated,
        repeated_count=len(deduplicated),
    )
