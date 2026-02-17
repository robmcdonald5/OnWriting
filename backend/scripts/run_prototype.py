"""CLI runner for the prototype pipeline.

Usage:
    poetry run python scripts/run_prototype.py "Your story prompt"
    poetry run python scripts/run_prototype.py  # Uses default prompt
"""

import sys
import time

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
        }
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
        print(f"\nStructure: {outline.total_scenes} scenes, {outline.total_beats} beats")

    # Drafts
    drafts = result.get("scene_drafts", [])
    total_words = sum(d.word_count for d in drafts)
    print(f"\nTotal word count: {total_words}")

    # Edit rounds
    feedback = result.get("edit_feedback", [])
    print(f"Edit rounds: {len(feedback)}")
    for fb in feedback:
        status = "APPROVED" if fb.approved else "REVISION NEEDED"
        print(f"  - Scene {fb.scene_id}: score={fb.quality_score:.2f} [{status}]")

    # Full manuscript
    print("\n" + "=" * 70)
    print("FULL MANUSCRIPT")
    print("=" * 70)
    for draft in drafts:
        print(f"\n--- Scene {draft.act_number}.{draft.scene_number} ---\n")
        print(draft.prose)
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
