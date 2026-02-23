"""CLI runner for the prototype pipeline.

Usage:
    poetry run python scripts/run_prototype.py "Your story prompt"
    poetry run python scripts/run_prototype.py  # Uses default prompt

To create a variant experiment, copy this file and modify STORY_CONFIG below.
"""

import sys
import time
from datetime import datetime
from pathlib import Path

from ai_writer.logging_config import configure_logging
from ai_writer.pipelines.prototype import build_prototype_pipeline
from ai_writer.prompts.configs import PrototypeConfig

# ═══════════════════════════════════════════════════════════════════════════
# PROTOTYPE CONFIGURATION
# All tunable parameters in one place. Copy this script and modify these
# values to run different experiments without touching agent code.
# ═══════════════════════════════════════════════════════════════════════════

STORY_CONFIG = PrototypeConfig(
    # ── Story Structure ──
    num_acts=1,
    scenes_per_act="2-3",
    num_themes="2-4",
    min_word_count=800,
    max_word_count=1200,
    # ── Tone Defaults (overridden at runtime by StoryBrief.tone_profile) ──
    default_formality=0.5,
    default_darkness=0.5,
    default_humor=0.3,
    default_pacing=0.5,
    prose_style="natural and engaging",
    # ── Editor Calibration ──
    normalization_guidance=(
        "Score STRICTLY. A score of 3 means 'competent but with clear "
        "weaknesses' — this is the expected score for a typical first draft. "
        "Score 4 ONLY when the criterion is met with zero weaknesses. "
        "Most first drafts should score 2-3 on most dimensions."
    ),
    # ── Pipeline Control ──
    max_revisions=2,
    min_revisions=1,
    # ── Agent Role Names ──
    story_brief_role="Plot Architect",
    character_roster_role="Casting Director",
    world_context_role="Lore Master",
    beat_outliner_role="Beat Outliner",
    scene_writer_role="Scene Writer",
    style_editor_role="Style Editor",
    # ── Closing Motivations ──
    story_brief_motivation=(
        "Be specific and creative. The brief drives all downstream writing."
    ),
    character_roster_motivation=(
        "Make characters feel real and distinct from each other."
    ),
    world_context_motivation="The world should feel consistent and lived-in.",
    beat_outliner_motivation=(
        "Be extremely specific. Scene Writers should make ZERO plot "
        "decisions — everything\nshould be predetermined in this outline."
    ),
    scene_writer_motivation=(
        "Output ONLY the scene prose. No headers, no meta-commentary."
    ),
)

DEFAULT_PROMPT = (
    "Write a short sci-fi story about a lone engineer on a deep-space relay station "
    "who intercepts a transmission that appears to come from a civilization that went "
    "extinct thousands of years ago. The story should explore themes of isolation, "
    "the weight of discovery, and what it means to be the only witness to something "
    "extraordinary. Tone: contemplative but with mounting tension. "
    "Keep it to 1 act with 2-3 scenes, roughly 2000-3000 words total."
)


def _format_feedback_entry(fb, max_reasoning: int = 200) -> list[str]:
    """Format a single EditFeedback entry into display lines.

    Used by both console and file output to avoid duplication.
    """
    r = fb.rubric
    status = "APPROVED" if fb.approved else "REVISION NEEDED"
    wc_status = "OK" if r.word_count_in_range else "OUT OF RANGE"
    tense_status = "consistent" if r.tense_consistent else "inconsistent"

    lines = [
        f"  Scene {fb.scene_id}: composite={fb.quality_score:.2f} [{status}]",
        f"    {r.dimension_summary()}",
        f"    word_count: {wc_status} | tense: {tense_status} | "
        f"slop: {r.slop_ratio:.2f}",
    ]

    # Structural flags
    struct_flags = []
    if r.opener_monotony:
        struct_flags.append("opener_monotony")
    if r.length_monotony:
        struct_flags.append("length_monotony")
    if r.passive_heavy:
        struct_flags.append("passive_heavy")
    if r.structural_monotony:
        struct_flags.append("structural_monotony")
    if struct_flags:
        lines.append(f"    structural: {', '.join(struct_flags)}")

    # Vocabulary flags
    vocab_flags = []
    if r.low_diversity:
        vocab_flags.append("low_diversity")
    if r.vocabulary_basic:
        vocab_flags.append("basic_vocabulary")
    if vocab_flags:
        lines.append(f"    vocabulary: {', '.join(vocab_flags)}")

    if r.cross_scene_repetitions > 0:
        lines.append(f"    cross_scene_repetitions: {r.cross_scene_repetitions}")
    if r.has_critical_failure():
        lines.append("    ** CRITICAL FAILURE on one or more dimensions **")
    if fb.confirmed_slop:
        lines.append(f"    confirmed_slop: {fb.confirmed_slop}")
    if r.dimension_reasoning:
        snippet = r.dimension_reasoning[:max_reasoning]
        if len(r.dimension_reasoning) > max_reasoning:
            snippet += "..."
        lines.append(f'    Reasoning: "{snippet}"')
    if fb.overall_assessment:
        lines.append(f"    Assessment: {fb.overall_assessment}")

    return lines


def _format_scene_metrics(scene_metrics) -> list[str]:
    """Format per-scene trend metrics into display lines."""
    if not scene_metrics:
        return []

    lines = ["", "SCENE METRICS"]
    lines.append("-" * 40)
    lines.append(
        f"  {'Scene':<8} {'Words':>6} {'Slop':>6} {'MTLD':>6} "
        f"{'Opener%':>8} {'LenCV':>6}"
    )
    for m in scene_metrics:
        lines.append(
            f"  {m.scene_id:<8} {m.word_count:>6} {m.slop_ratio:>6.2f} "
            f"{m.mtld:>6.1f} {m.opener_ratio:>7.1%} {m.sent_length_cv:>6.2f}"
        )
    return lines


def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT

    # Set up output directory and log file
    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = str(output_dir / f"{timestamp}_pipeline.log")

    configure_logging(level="INFO", log_file=log_path)

    print("=" * 70)
    print("AI CREATIVE WRITING ASSISTANT — PROTOTYPE PIPELINE")
    print("=" * 70)
    print(f"\nPrompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n")

    # Build and run pipeline
    pipeline = build_prototype_pipeline()

    print("Running pipeline...")
    start = time.time()

    # Recursion limit: 2 planning nodes + n_scenes * (3 * max_revisions + 3).
    # With 5 scenes and 2 revisions: 2 + 5*9 = 47. Use 50 for headroom.
    result = pipeline.invoke(
        {
            "user_prompt": prompt,
            "scene_drafts": [],
            "edit_feedback": [],
            "scene_metrics": [],
            "current_scene_index": 0,
            "revision_count": 0,
            "max_revisions": STORY_CONFIG.max_revisions,
            "min_revisions": STORY_CONFIG.min_revisions,
            "current_stage": "planning",
            "errors": [],
            "prompt_configs": STORY_CONFIG.to_prompt_configs(),
        },
        config={"recursion_limit": 50},
    )

    elapsed = time.time() - start

    # Display results
    print(f"\nPipeline completed in {elapsed:.1f}s")
    print("-" * 70)

    # Story Brief
    brief = result.get("story_brief")
    if brief:
        print(f"\nTitle: {brief.title}")
        print(f"Genre: {brief.genre.value}")
        print(f"Themes: {', '.join(brief.themes)}")
        print(f"Premise: {brief.premise}")

    # Characters
    roster = result.get("character_roster")
    if roster:
        print(f"\nCharacters ({len(roster.characters)}):")
        for c in roster.characters:
            print(f"  - {c.name} ({c.role.value}): {c.motivation}")

    # Structure
    outline = result.get("story_outline")
    if outline:
        print(
            f"\nStructure: {outline.total_scenes} scenes, {outline.total_beats} beats"
        )

    # Drafts
    drafts = result.get("scene_drafts", [])
    total_words = sum(d.word_count for d in drafts)
    print(f"\nTotal word count: {total_words}")

    # Edit rounds
    feedback = result.get("edit_feedback", [])
    print(f"Edit rounds: {len(feedback)}")
    for fb in feedback:
        for line in _format_feedback_entry(fb):
            print(line)

    # Scene metrics
    scene_metrics = result.get("scene_metrics", [])
    for line in _format_scene_metrics(scene_metrics):
        print(line)

    # Full manuscript
    print("\n" + "=" * 70)
    print("FULL MANUSCRIPT")
    print("=" * 70)
    for draft in drafts:
        print(f"\n--- Scene {draft.act_number}.{draft.scene_number} ---\n")
        print(draft.prose)
    print("\n" + "=" * 70)

    # Save output to file
    title_slug = brief.title.lower().replace(" ", "_")[:40] if brief else "untitled"
    output_path = output_dir / f"{timestamp}_{title_slug}.txt"

    lines = []
    lines.append(f"Title: {brief.title}" if brief else "Title: Unknown")
    lines.append(f"Genre: {brief.genre.value}" if brief else "")
    lines.append(f"Themes: {', '.join(brief.themes)}" if brief else "")
    lines.append(f"Premise: {brief.premise}" if brief else "")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append(f"Pipeline time: {elapsed:.1f}s")
    lines.append(f"Total words: {total_words}")
    lines.append("")

    if roster:
        lines.append("CHARACTERS")
        lines.append("-" * 40)
        for c in roster.characters:
            lines.append(f"  {c.name} ({c.role.value}): {c.motivation}")
        lines.append("")

    if feedback:
        lines.append("EDIT FEEDBACK")
        lines.append("-" * 40)
        for fb in feedback:
            lines.extend(_format_feedback_entry(fb, max_reasoning=300))
        lines.append("")

    lines.extend(_format_scene_metrics(scene_metrics))

    lines.append("")
    lines.append("=" * 70)
    lines.append("MANUSCRIPT")
    lines.append("=" * 70)
    for draft in drafts:
        lines.append(f"\n--- Scene {draft.act_number}.{draft.scene_number} ---\n")
        lines.append(draft.prose)

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nOutput saved to: {output_path}")
    print(f"Log saved to: {log_path}")


if __name__ == "__main__":
    main()
