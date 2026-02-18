"""CLI runner for the prototype pipeline.

Usage:
    poetry run python scripts/run_prototype.py "Your story prompt"
    poetry run python scripts/run_prototype.py  # Uses default prompt
"""

import sys
import time
from datetime import datetime
from pathlib import Path

from ai_writer.pipelines.prototype import build_prototype_pipeline

DEFAULT_PROMPT = (
    "Write a short sci-fi story about a lone engineer on a deep-space relay station "
    "who intercepts a transmission that appears to come from a civilization that went "
    "extinct thousands of years ago. The story should explore themes of isolation, "
    "the weight of discovery, and what it means to be the only witness to something "
    "extraordinary. Tone: contemplative but with mounting tension. "
    "Keep it to 1 act with 2-3 scenes, roughly 2000-3000 words total."
)


def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT

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
            "current_scene_index": 0,
            "revision_count": 0,
            "max_revisions": 2,
            "current_stage": "planning",
            "errors": [],
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
        status = "APPROVED" if fb.approved else "REVISION NEEDED"
        r = fb.rubric
        print(f"  Scene {fb.scene_id}: composite={fb.quality_score:.2f} [{status}]")
        print(f"    {r.dimension_summary()}")
        wc_status = "OK" if r.word_count_in_range else "OUT OF RANGE"
        tense_status = "consistent" if r.tense_consistent else "inconsistent"
        print(
            f"    word_count: {wc_status} | tense: {tense_status} | "
            f"slop: {r.slop_ratio:.2f}"
        )
        if r.has_critical_failure():
            print("    ** CRITICAL FAILURE on one or more dimensions **")
        if r.dimension_reasoning:
            # Show first 200 chars of reasoning
            snippet = r.dimension_reasoning[:200]
            if len(r.dimension_reasoning) > 200:
                snippet += "..."
            print(f'    Reasoning: "{snippet}"')

    # Full manuscript
    print("\n" + "=" * 70)
    print("FULL MANUSCRIPT")
    print("=" * 70)
    for draft in drafts:
        print(f"\n--- Scene {draft.act_number}.{draft.scene_number} ---\n")
        print(draft.prose)
    print("\n" + "=" * 70)

    # Save output to file
    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
            status = "APPROVED" if fb.approved else "REVISION NEEDED"
            r = fb.rubric
            lines.append(
                f"  Scene {fb.scene_id}: composite={fb.quality_score:.2f} [{status}]"
            )
            lines.append(f"    {r.dimension_summary()}")
            wc_status = "OK" if r.word_count_in_range else "OUT OF RANGE"
            tense_status = "consistent" if r.tense_consistent else "inconsistent"
            lines.append(
                f"    word_count: {wc_status} | tense: {tense_status} | "
                f"slop: {r.slop_ratio:.2f}"
            )
            if r.dimension_reasoning:
                lines.append(f"    Reasoning: {r.dimension_reasoning[:300]}")
            if fb.overall_assessment:
                lines.append(f"    Assessment: {fb.overall_assessment}")
        lines.append("")

    lines.append("=" * 70)
    lines.append("MANUSCRIPT")
    lines.append("=" * 70)
    for draft in drafts:
        lines.append(f"\n--- Scene {draft.act_number}.{draft.scene_number} ---\n")
        lines.append(draft.prose)

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
