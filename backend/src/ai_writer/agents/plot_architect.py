"""Plot Architect agent — combines Architect + Casting Director + Lore Master.

Three sequential LLM calls with planning_temperature (0.3):
1. User prompt → StoryBrief
2. StoryBrief → CharacterRoster
3. StoryBrief → WorldContext
"""

from ai_writer.agents.base import get_structured_llm, invoke
from ai_writer.config import get_settings
from ai_writer.prompts.builders import (
    build_character_roster_prompt,
    build_story_brief_prompt,
    build_world_context_prompt,
)
from ai_writer.prompts.configs import (
    CharacterRosterPromptConfig,
    StoryBriefPromptConfig,
    WorldContextPromptConfig,
)
from ai_writer.schemas.characters import CharacterRoster
from ai_writer.schemas.story import StoryBrief
from ai_writer.schemas.world import WorldContext


def run_plot_architect(state: dict) -> dict:
    """Execute the Plot Architect agent: user_prompt → StoryBrief + CharacterRoster + WorldContext."""
    settings = get_settings()
    temp = settings.planning_temperature
    user_prompt = state["user_prompt"]

    configs = state.get("prompt_configs", {})
    brief_config = configs.get("story_brief", StoryBriefPromptConfig())
    roster_config = configs.get("character_roster", CharacterRosterPromptConfig())
    world_config = configs.get("world_context", WorldContextPromptConfig())

    # 1. Generate StoryBrief
    print("  [Plot Architect] Generating story brief...", flush=True)
    brief_llm = get_structured_llm(StoryBrief, temperature=temp)
    story_brief = invoke(
        brief_llm,
        [
            {"role": "system", "content": build_story_brief_prompt(brief_config)},
            {"role": "user", "content": user_prompt},
        ],
    )

    # 2. Generate CharacterRoster
    print(f'  [Plot Architect] Brief done: "{story_brief.title}"', flush=True)
    print("  [Plot Architect] Generating character roster...", flush=True)
    roster_llm = get_structured_llm(CharacterRoster, temperature=temp)
    character_roster = invoke(
        roster_llm,
        [
            {"role": "system", "content": build_character_roster_prompt(roster_config)},
            {
                "role": "user",
                "content": f"Create characters for this story:\n\n{story_brief.model_dump_json(indent=2)}",
            },
        ],
    )

    # 3. Generate WorldContext
    print(
        f"  [Plot Architect] Roster done: {len(character_roster.characters)} characters",
        flush=True,
    )
    print("  [Plot Architect] Generating world context...", flush=True)
    world_llm = get_structured_llm(WorldContext, temperature=temp)
    world_context = invoke(
        world_llm,
        [
            {"role": "system", "content": build_world_context_prompt(world_config)},
            {
                "role": "user",
                "content": f"Create the world for this story:\n\n{story_brief.model_dump_json(indent=2)}",
            },
        ],
    )

    print(
        f"  [Plot Architect] World done: {len(world_context.locations)} locations, {len(world_context.rules)} rules",
        flush=True,
    )

    return {
        "story_brief": story_brief,
        "character_roster": character_roster,
        "world_context": world_context,
        "current_stage": "outlining",
    }
