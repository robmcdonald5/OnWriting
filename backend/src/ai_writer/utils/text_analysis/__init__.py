"""Deterministic text analysis utilities — zero LLM cost.

Public API re-exports for backward compatibility:
    from ai_writer.utils.text_analysis import compute_slop_score
    from ai_writer.utils.text_analysis import check_word_count
    from ai_writer.utils.text_analysis import check_tense_consistency
"""

from ai_writer.prompts.configs import ProseStructureConfig, SlopConfig, VocabularyConfig
from ai_writer.utils.text_analysis.basics import (
    TenseResult,
    WordCountResult,
    check_tense_consistency,
    check_word_count,
)
from ai_writer.utils.text_analysis.context import build_story_allowlist
from ai_writer.utils.text_analysis.repetition import (
    CrossSceneRepetitionResult,
    detect_cross_scene_repetition,
)
from ai_writer.utils.text_analysis.slop import SlopResult, compute_slop_score
from ai_writer.utils.text_analysis.structure import (
    ProseStructureResult,
    compute_prose_structure,
)
from ai_writer.utils.text_analysis.vocabulary import (
    VocabularyResult,
    compute_vocabulary_metrics,
)

__all__ = [
    # Basics
    "WordCountResult",
    "check_word_count",
    "TenseResult",
    "check_tense_consistency",
    # Slop
    "SlopConfig",
    "SlopResult",
    "compute_slop_score",
    # Context
    "build_story_allowlist",
    # Repetition
    "CrossSceneRepetitionResult",
    "detect_cross_scene_repetition",
    # Structure
    "ProseStructureConfig",
    "ProseStructureResult",
    "compute_prose_structure",
    # Vocabulary
    "VocabularyConfig",
    "VocabularyResult",
    "compute_vocabulary_metrics",
]
