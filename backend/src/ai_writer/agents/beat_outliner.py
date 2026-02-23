"""Beat Outliner agent — breaks the story brief into narrative beats and scene outlines.

Single LLM call: StoryBrief + CharacterRoster + WorldContext -> StoryOutline
"""

import logging

from ai_writer.agents.base import get_structured_llm, invoke
from ai_writer.config import get_settings
from ai_writer.prompts.builders import build_beat_outliner_prompt
from ai_writer.prompts.configs import BeatOutlinerPromptConfig
from ai_writer.schemas.structure import StoryOutline

logger = logging.getLogger("ai_writer.agents.beat_outliner")


def run_beat_outliner(state: dict) -> dict:
    """Execute the Beat Outliner: StoryBrief + CharacterRoster + WorldContext -> StoryOutline."""
    settings = get_settings()
    temp = settings.planning_temperature

    story_brief = state["story_brief"]
    character_roster = state["character_roster"]
    world_context = state["world_context"]

    configs = state.get("prompt_configs", {})
    config = configs.get("beat_outliner", BeatOutlinerPromptConfig())

    logger.info("Building story outline...")
    outline_llm = get_structured_llm(StoryOutline, temperature=temp)

    context = (
        f"## Story Brief\n{story_brief.model_dump_json(indent=2)}\n\n"
        f"## Character Roster\n{character_roster.model_dump_json(indent=2)}\n\n"
        f"## World Context\n{world_context.model_dump_json(indent=2)}"
    )

    story_outline = invoke(
        outline_llm,
        [
            {"role": "system", "content": build_beat_outliner_prompt(config)},
            {
                "role": "user",
                "content": f"Create a detailed story outline:\n\n{context}",
            },
        ],
    )

    logger.info(
        "Outline done: %d scenes, %d beats",
        story_outline.total_scenes,
        story_outline.total_beats,
    )

    return {
        "story_outline": story_outline,
        "current_stage": "writing",
    }
