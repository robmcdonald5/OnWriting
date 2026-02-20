"""Loader for vendored slop detection data from sam-paech/antislop-sampler.

Data files:
- slop_phrases.json: [[phrase, prob_multiplier], ...] — 517 entries.
  Lower prob_multiplier = more aggressively suppressed = higher AI signal.
- slop_words.json: [[word, corpus_count], ...] — 2000 entries.
  Higher corpus_count = more overrepresented in LLM output vs human baselines.

Both files are loaded once at import time and cached.
"""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent

# ── Lazy-loaded caches ────────────────────────────────────────────────────

_phrases_cache: list[tuple[str, float]] | None = None
_words_cache: list[tuple[str, float]] | None = None


def _load_phrases() -> list[tuple[str, float]]:
    """Load phrase data, converting prob multiplier to a penalty weight.

    Penalty = 1.0 - prob_multiplier, so:
    - prob 0.03125 → penalty 0.96875 (strongest AI signal)
    - prob 0.50    → penalty 0.50    (moderate signal)
    """
    raw = json.loads((_DATA_DIR / "slop_phrases.json").read_text(encoding="utf-8"))
    return [(phrase, round(1.0 - prob, 4)) for phrase, prob in raw]


def _load_words() -> list[tuple[str, float]]:
    """Load word data, normalizing corpus counts to [0, 1] penalty weights.

    Normalization: count / max_count, so the most overrepresented word = 1.0.
    """
    raw = json.loads((_DATA_DIR / "slop_words.json").read_text(encoding="utf-8"))
    if not raw:
        return []
    max_count = max(count for _, count in raw)
    return [(word, round(count / max_count, 4)) for word, count in raw]


def get_slop_phrases(min_severity: float = 0.0) -> list[tuple[str, float]]:
    """Return slop phrases with penalty weights.

    Args:
        min_severity: Minimum penalty weight to include (0.0 = all, 0.9 = only
            the strongest signals). Default returns all phrases.

    Returns:
        List of (phrase, penalty_weight) tuples sorted by weight descending.
    """
    global _phrases_cache
    if _phrases_cache is None:
        _phrases_cache = _load_phrases()
    filtered = [(p, w) for p, w in _phrases_cache if w >= min_severity]
    return sorted(filtered, key=lambda x: x[1], reverse=True)


def get_slop_words(min_severity: float = 0.0) -> list[tuple[str, float]]:
    """Return overrepresented words with normalized penalty weights.

    Args:
        min_severity: Minimum penalty weight to include (0.0 = all, 0.5 = top
            half of overrepresentation). Default returns all words.

    Returns:
        List of (word, penalty_weight) tuples sorted by weight descending.
    """
    global _words_cache
    if _words_cache is None:
        _words_cache = _load_words()
    filtered = [(w, wt) for w, wt in _words_cache if wt >= min_severity]
    return sorted(filtered, key=lambda x: x[1], reverse=True)
