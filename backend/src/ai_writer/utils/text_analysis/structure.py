"""Structural monotony analysis using spaCy.

Detects predictable, repetitive prose patterns that are hallmarks of
AI-generated writing: uniform sentence openings, low sentence-length
variation, excessive passive voice, and structurally simple sentences.

All analysis reuses the lazy-cached spaCy model from basics._get_nlp().
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from ai_writer.prompts.configs import ProseStructureConfig
from ai_writer.utils.text_analysis.basics import _get_nlp


@dataclass
class ProseStructureResult:
    """Structural monotony analysis results."""

    sentence_count: int = 0
    # Sentence openings
    top_opener_pos: str = ""  # e.g. "PRON"
    top_opener_ratio: float = 0.0  # e.g. 0.45 = 45% start with pronoun
    opener_monotony: bool = False  # True if top_opener_ratio > threshold
    # Sentence length variation
    sent_length_mean: float = 0.0
    sent_length_std: float = 0.0
    sent_length_cv: float = 0.0  # coefficient of variation (std/mean)
    length_monotony: bool = False  # True if CV < threshold
    # Passive voice
    passive_count: int = 0
    passive_ratio: float = 0.0
    passive_heavy: bool = False  # True if ratio > threshold
    # Dependency distance
    dep_distance_mean: float = 0.0
    dep_distance_std: float = 0.0
    structural_monotony: bool = False  # True if dep std < threshold

    def summary_lines(self) -> list[str]:
        """Return human-readable summary lines for flagged issues only."""
        lines: list[str] = []
        if self.opener_monotony:
            lines.append(
                f"Sentence opener monotony: {self.top_opener_ratio:.0%} of sentences "
                f"start with {self.top_opener_pos}"
            )
        if self.length_monotony:
            lines.append(f"Sentence length CV: {self.sent_length_cv:.2f} — low variety")
        if self.passive_heavy:
            lines.append(f"Passive voice: {self.passive_ratio:.0%}")
        if self.structural_monotony:
            lines.append(
                f"Dependency distance std: {self.dep_distance_std:.2f} — "
                "structurally simple"
            )
        return lines


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: Sequence[float], mean: float) -> float:
    if len(values) < 2:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance**0.5


def compute_prose_structure(
    prose: str,
    config: ProseStructureConfig | None = None,
) -> ProseStructureResult:
    """Analyze prose for structural monotony patterns.

    Runs spaCy on the full prose text and computes:
    1. Sentence opening POS distribution (pronoun-heavy = monotonous)
    2. Sentence length variation (low CV = uniform/predictable)
    3. Passive voice ratio (>20% = over-reliance)
    4. Dependency distance variation (low std = simple SVO patterns)

    Args:
        prose: The text to analyze.
        config: Threshold configuration. Uses defaults if None.

    Returns:
        ProseStructureResult with all metrics and boolean flags.
    """
    if config is None:
        config = ProseStructureConfig()

    nlp = _get_nlp()
    if nlp is None:
        return ProseStructureResult()

    doc = nlp(prose)
    sentences = list(doc.sents)
    sentence_count = len(sentences)

    if sentence_count == 0:
        return ProseStructureResult()

    # --- Sentence openings ---
    opener_pos_counts: Counter[str] = Counter()
    for sent in sentences:
        # Skip leading whitespace/punctuation to find the real first token
        for token in sent:
            if not token.is_space and not token.is_punct:
                opener_pos_counts[token.pos_] += 1
                break

    if opener_pos_counts:
        top_pos, top_count = opener_pos_counts.most_common(1)[0]
        top_ratio = top_count / sentence_count
    else:
        top_pos, top_ratio = "", 0.0

    # --- Sentence length variation ---
    sent_lengths = [
        len([t for t in sent if not t.is_space and not t.is_punct])
        for sent in sentences
    ]
    length_mean = _mean(sent_lengths)
    length_std = _std(sent_lengths, length_mean)
    length_cv = (length_std / length_mean) if length_mean > 0 else 0.0

    # --- Passive voice detection ---
    # spaCy marks passive subjects with nsubjpass and passive auxiliaries with auxpass
    passive_count = 0
    for sent in sentences:
        has_passive = any(token.dep_ in ("nsubjpass", "auxpass") for token in sent)
        if has_passive:
            passive_count += 1
    passive_ratio = passive_count / sentence_count

    # --- Dependency distance variation ---
    # Distance = abs(token.i - token.head.i) for non-root tokens
    dep_distances: list[float] = []
    for token in doc:
        if token.dep_ != "ROOT" and not token.is_space:
            dep_distances.append(float(abs(token.i - token.head.i)))

    dep_mean = _mean(dep_distances)
    dep_std = _std(dep_distances, dep_mean)

    return ProseStructureResult(
        sentence_count=sentence_count,
        # Openings
        top_opener_pos=top_pos,
        top_opener_ratio=round(top_ratio, 3),
        opener_monotony=top_ratio > config.opener_monotony_threshold,
        # Sentence length
        sent_length_mean=round(length_mean, 1),
        sent_length_std=round(length_std, 1),
        sent_length_cv=round(length_cv, 3),
        length_monotony=length_cv < config.length_cv_threshold,
        # Passive voice
        passive_count=passive_count,
        passive_ratio=round(passive_ratio, 3),
        passive_heavy=passive_ratio > config.passive_ratio_threshold,
        # Dependency distance
        dep_distance_mean=round(dep_mean, 2),
        dep_distance_std=round(dep_std, 2),
        structural_monotony=dep_std < config.dep_distance_std_threshold,
    )
