"""Pydantic config models defining the configurable surface for each agent's prompt.

Two levels of configuration:

1. **PrototypeConfig** (script-level) — A single flat model with every tunable
   parameter. This is what prototype scripts define at the top of the file.
   Call `to_prompt_configs()` to fan out into per-agent dicts for the pipeline.

2. **Per-agent configs** (internal) — Individual models used by agents to read
   their settings. Scripts rarely create these directly; PrototypeConfig builds
   them via `to_prompt_configs()`.

Usage:
    # In a prototype script — define everything in one place:
    config = PrototypeConfig(
        num_acts=2,
        scenes_per_act="3-4",
        prose_style="sparse and stark",
        max_revisions=3,
    )
    result = pipeline.invoke({
        "user_prompt": prompt,
        "prompt_configs": config.to_prompt_configs(),
        "max_revisions": config.max_revisions,
        "min_revisions": config.min_revisions,
        ...
    })
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StoryBriefPromptConfig(BaseModel):
    """Variables for Plot Architect (StoryBrief) system prompt."""

    role_name: str = "Plot Architect"
    num_themes: str = "2-4"
    num_acts: int = 1
    scenes_per_act: str = "2-3"
    min_word_count: int = 800
    max_word_count: int = 1200
    closing_motivation: str = (
        "Be specific and creative. The brief drives all downstream writing."
    )


class CharacterRosterPromptConfig(BaseModel):
    """Variables for Plot Architect (CharacterRoster) system prompt."""

    role_name: str = "Casting Director"
    closing_motivation: str = "Make characters feel real and distinct from each other."


class WorldContextPromptConfig(BaseModel):
    """Variables for Plot Architect (WorldContext) system prompt."""

    role_name: str = "Lore Master"
    closing_motivation: str = "The world should feel consistent and lived-in."


class BeatOutlinerPromptConfig(BaseModel):
    """Variables for Beat Outliner system prompt."""

    role_name: str = "Beat Outliner"
    closing_motivation: str = Field(
        default=(
            "Be extremely specific. Scene Writers should make ZERO plot decisions "
            "— everything\nshould be predetermined in this outline."
        )
    )


class SceneWriterPromptConfig(BaseModel):
    """Variables for Scene Writer system prompt.

    Tone values (formality, darkness, humor, pacing) default here but are
    overridden at runtime from the StoryBrief's tone_profile.
    """

    role_name: str = "Scene Writer"
    formality: float = 0.5
    darkness: float = 0.5
    humor: float = 0.3
    pacing: float = 0.5
    prose_style: str = "natural and engaging"
    target_word_count: int = 1000
    closing_motivation: str = (
        "Output ONLY the scene prose. No headers, no meta-commentary."
    )


class SlopConfig(BaseModel):
    """Scoring parameters for slop detection."""

    phrase_penalty_scale: float = 10.0  # multiplier in ratio formula
    word_excess_weight: float = 0.3  # penalty per excess word occurrence
    word_min_severity: float = 0.5  # minimum severity for word-level scan
    word_free_occurrences: int = 1  # free occurrences before penalty


class ProseStructureConfig(BaseModel):
    """Thresholds for structural monotony detection."""

    opener_monotony_threshold: float = 0.30  # >30% same POS opener
    length_cv_threshold: float = 0.30  # CV below this = monotonous
    passive_ratio_threshold: float = 0.20  # >20% passive
    dep_distance_std_threshold: float = 0.50  # std below this = simple SVO


class VocabularyConfig(BaseModel):
    """Thresholds for vocabulary analysis."""

    mtld_threshold: float = 60.0  # below = low diversity
    zipf_threshold: float = 5.5  # above = overly common vocabulary
    mattr_window: int = 50


class ScoreCapConfig(BaseModel):
    """Deterministic score caps applied after LLM scoring.

    When automated metrics fail thresholds, Python hard-caps the LLM score
    rather than relying on advisory language the LLM may ignore.
    """

    cap_pacing_on_monotony: int = 2
    cap_prose_on_slop_count: int = 3  # threshold: confirmed_slop >= this
    cap_prose_on_slop_value: int = 2  # cap to this value
    cap_prose_on_low_diversity: int = 3


class AdvisoryPenaltyConfig(BaseModel):
    """Soft penalty values for advisory metrics in compute_quality_score().

    Calibrated for the 1-4 normalization range. Max structural: 0.12,
    max vocabulary: 0.06, max cross-scene: 0.06. Total max: 0.24.
    """

    opener_monotony: float = 0.04
    length_monotony: float = 0.04
    passive_heavy: float = 0.02
    structural_monotony: float = 0.02
    low_diversity: float = 0.04
    vocabulary_basic: float = 0.02
    cross_scene_per: float = 0.02
    cross_scene_max: int = 3


class StyleEditorPromptConfig(BaseModel):
    """Variables for Style Editor system prompt.

    Tone values default here but are overridden at runtime from tone_profile.
    """

    role_name: str = "Style Editor"
    formality: float = 0.5
    darkness: float = 0.5
    humor: float = 0.3
    pacing: float = 0.5
    normalization_guidance: str = (
        "Score STRICTLY. A score of 3 means 'competent but with clear "
        "weaknesses' — this is the expected score for a typical first draft. "
        "Score 4 ONLY when the criterion is met with zero weaknesses. "
        "Most first drafts should score 2-3 on most dimensions."
    )


# ── Script-Level Configuration ──────────────────────────────────────────────


class PrototypeConfig(BaseModel):
    """Top-level configuration for a prototype pipeline run.

    Every tunable parameter is defined here as a flat field. Prototype scripts
    set all values at the top of the file, then call ``to_prompt_configs()``
    to build the per-agent dict the pipeline expects.

    To create a new experiment, copy a script and change these values.
    """

    # ── Story Structure ──────────────────────────────────────────────
    num_acts: int = 1
    scenes_per_act: str = "2-3"
    num_themes: str = "2-4"
    min_word_count: int = 800
    max_word_count: int = 1200

    # ── Tone Defaults ────────────────────────────────────────────────
    # Fallback tone for SceneWriter / StyleEditor.  At runtime the actual
    # values come from StoryBrief.tone_profile and override these.
    default_formality: float = 0.5
    default_darkness: float = 0.5
    default_humor: float = 0.3
    default_pacing: float = 0.5
    prose_style: str = "natural and engaging"

    # ── Editor Calibration ───────────────────────────────────────────
    normalization_guidance: str = (
        "Score STRICTLY. A score of 3 means 'competent but with clear "
        "weaknesses' — this is the expected score for a typical first draft. "
        "Score 4 ONLY when the criterion is met with zero weaknesses. "
        "Most first drafts should score 2-3 on most dimensions."
    )

    # ── Score Caps (deterministic overrides after LLM scoring) ──────
    cap_pacing_on_monotony: int = 2
    cap_prose_on_slop_count: int = 3
    cap_prose_on_slop_value: int = 2
    cap_prose_on_low_diversity: int = 3

    # ── Advisory Penalty Values ─────────────────────────────────────
    penalty_opener_monotony: float = 0.04
    penalty_length_monotony: float = 0.04
    penalty_passive_heavy: float = 0.02
    penalty_structural_monotony: float = 0.02
    penalty_low_diversity: float = 0.04
    penalty_vocabulary_basic: float = 0.02
    penalty_cross_scene_per: float = 0.02
    penalty_cross_scene_max: int = 3

    # ── Prose Structure Thresholds ────────────────────────────────────
    opener_monotony_threshold: float = 0.30
    length_cv_threshold: float = 0.30
    passive_ratio_threshold: float = 0.20
    dep_distance_std_threshold: float = 0.50

    # ── Vocabulary Thresholds ─────────────────────────────────────────
    mtld_threshold: float = 60.0
    zipf_threshold: float = 5.5
    mattr_window: int = 50

    # ── Slop Detection ─────────────────────────────────────────────
    slop_phrase_penalty_scale: float = 10.0
    slop_word_excess_weight: float = 0.3
    slop_word_min_severity: float = 0.5
    slop_word_free_occurrences: int = 1

    # ── Pipeline Control ─────────────────────────────────────────────
    max_revisions: int = 2
    min_revisions: int = 1  # guaranteed editing pass(es) per scene

    # ── Agent Role Names ─────────────────────────────────────────────
    story_brief_role: str = "Plot Architect"
    character_roster_role: str = "Casting Director"
    world_context_role: str = "Lore Master"
    beat_outliner_role: str = "Beat Outliner"
    scene_writer_role: str = "Scene Writer"
    style_editor_role: str = "Style Editor"

    # ── Closing Motivations (per-agent) ──────────────────────────────
    story_brief_motivation: str = (
        "Be specific and creative. The brief drives all downstream writing."
    )
    character_roster_motivation: str = (
        "Make characters feel real and distinct from each other."
    )
    world_context_motivation: str = "The world should feel consistent and lived-in."
    beat_outliner_motivation: str = Field(
        default=(
            "Be extremely specific. Scene Writers should make ZERO plot "
            "decisions — everything\nshould be predetermined in this outline."
        )
    )
    scene_writer_motivation: str = (
        "Output ONLY the scene prose. No headers, no meta-commentary."
    )

    def to_prompt_configs(self) -> dict[str, Any]:
        """Convert flat config into the per-agent ``prompt_configs`` dict.

        Returns a dict keyed by agent name, suitable for passing directly
        into the pipeline's ``prompt_configs`` state field.
        """
        return {
            "story_brief": StoryBriefPromptConfig(
                role_name=self.story_brief_role,
                num_themes=self.num_themes,
                num_acts=self.num_acts,
                scenes_per_act=self.scenes_per_act,
                min_word_count=self.min_word_count,
                max_word_count=self.max_word_count,
                closing_motivation=self.story_brief_motivation,
            ),
            "character_roster": CharacterRosterPromptConfig(
                role_name=self.character_roster_role,
                closing_motivation=self.character_roster_motivation,
            ),
            "world_context": WorldContextPromptConfig(
                role_name=self.world_context_role,
                closing_motivation=self.world_context_motivation,
            ),
            "beat_outliner": BeatOutlinerPromptConfig(
                role_name=self.beat_outliner_role,
                closing_motivation=self.beat_outliner_motivation,
            ),
            "scene_writer": SceneWriterPromptConfig(
                role_name=self.scene_writer_role,
                formality=self.default_formality,
                darkness=self.default_darkness,
                humor=self.default_humor,
                pacing=self.default_pacing,
                prose_style=self.prose_style,
                closing_motivation=self.scene_writer_motivation,
            ),
            "style_editor": StyleEditorPromptConfig(
                role_name=self.style_editor_role,
                formality=self.default_formality,
                darkness=self.default_darkness,
                humor=self.default_humor,
                pacing=self.default_pacing,
                normalization_guidance=self.normalization_guidance,
            ),
            "prose_structure": ProseStructureConfig(
                opener_monotony_threshold=self.opener_monotony_threshold,
                length_cv_threshold=self.length_cv_threshold,
                passive_ratio_threshold=self.passive_ratio_threshold,
                dep_distance_std_threshold=self.dep_distance_std_threshold,
            ),
            "vocabulary": VocabularyConfig(
                mtld_threshold=self.mtld_threshold,
                zipf_threshold=self.zipf_threshold,
                mattr_window=self.mattr_window,
            ),
            "slop": SlopConfig(
                phrase_penalty_scale=self.slop_phrase_penalty_scale,
                word_excess_weight=self.slop_word_excess_weight,
                word_min_severity=self.slop_word_min_severity,
                word_free_occurrences=self.slop_word_free_occurrences,
            ),
            "score_caps": ScoreCapConfig(
                cap_pacing_on_monotony=self.cap_pacing_on_monotony,
                cap_prose_on_slop_count=self.cap_prose_on_slop_count,
                cap_prose_on_slop_value=self.cap_prose_on_slop_value,
                cap_prose_on_low_diversity=self.cap_prose_on_low_diversity,
            ),
            "advisory_penalties": AdvisoryPenaltyConfig(
                opener_monotony=self.penalty_opener_monotony,
                length_monotony=self.penalty_length_monotony,
                passive_heavy=self.penalty_passive_heavy,
                structural_monotony=self.penalty_structural_monotony,
                low_diversity=self.penalty_low_diversity,
                vocabulary_basic=self.penalty_vocabulary_basic,
                cross_scene_per=self.penalty_cross_scene_per,
                cross_scene_max=self.penalty_cross_scene_max,
            ),
        }
