"""Plot Architect agent — combines Architect + Casting Director + Lore Master.

Three sequential LLM calls with planning_temperature (0.3):
1. User prompt → StoryBrief
2. StoryBrief → CharacterRoster
3. StoryBrief → WorldContext
"""

from ai_writer.agents.base import get_structured_llm
from ai_writer.config import get_settings
from ai_writer.schemas.characters import CharacterRoster
from ai_writer.schemas.story import StoryBrief
from ai_writer.schemas.world import WorldContext

STORY_BRIEF_SYSTEM = """You are a Plot Architect for a creative writing system.
Given a user's story prompt, produce a detailed StoryBrief.

Guidelines:
- Choose a genre that best fits the prompt
- Extract 2-4 strong themes
- Write a 1-2 sentence premise that captures the core conflict
- Create a compelling title
- Set scope to 1 act with 2-3 scenes (this is a short story prototype)
- Set target_scene_word_count between 800-1200 words
- Configure the tone_profile with numeric values (0.0-1.0) that match the story's mood
- Set target_audience appropriately

Be specific and creative. The brief drives all downstream writing."""

CHARACTER_ROSTER_SYSTEM = """You are a Casting Director for a creative writing system.
Given a StoryBrief, create a CharacterRoster with 2-4 characters for a short story.

Guidelines:
- Every story needs at least a protagonist
- Give each character a unique character_id (e.g. "c1", "c2")
- Write distinct voice_notes and speech_patterns for each character
- Define clear motivations and internal conflicts
- Add at least one relationship between characters
- Keep backstories brief — this is a short story
- personality_traits should be 3-5 specific adjectives

Make characters feel real and distinct from each other."""

WORLD_CONTEXT_SYSTEM = """You are a Lore Master for a creative writing system.
Given a StoryBrief, create a WorldContext with the setting details.

Guidelines:
- Define the setting_period and setting_description clearly
- Create 1-3 locations that the story will use
- Give each location a unique location_id (e.g. "loc1", "loc2")
- Add 1-3 world rules that constrain/enrich the story
- Give each rule a unique rule_id (e.g. "r1", "r2")
- Include 2-4 key_facts that writers should know
- Keep it focused — only details relevant to this short story

The world should feel consistent and lived-in."""


def run_plot_architect(state: dict) -> dict:
    """Execute the Plot Architect agent: user_prompt → StoryBrief + CharacterRoster + WorldContext."""
    settings = get_settings()
    temp = settings.planning_temperature
    user_prompt = state["user_prompt"]

    # 1. Generate StoryBrief
    brief_llm = get_structured_llm(StoryBrief, temperature=temp)
    story_brief = brief_llm.invoke(
        [
            {"role": "system", "content": STORY_BRIEF_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]
    )

    # 2. Generate CharacterRoster
    roster_llm = get_structured_llm(CharacterRoster, temperature=temp)
    character_roster = roster_llm.invoke(
        [
            {"role": "system", "content": CHARACTER_ROSTER_SYSTEM},
            {
                "role": "user",
                "content": f"Create characters for this story:\n\n{story_brief.model_dump_json(indent=2)}",
            },
        ]
    )

    # 3. Generate WorldContext
    world_llm = get_structured_llm(WorldContext, temperature=temp)
    world_context = world_llm.invoke(
        [
            {"role": "system", "content": WORLD_CONTEXT_SYSTEM},
            {
                "role": "user",
                "content": f"Create the world for this story:\n\n{story_brief.model_dump_json(indent=2)}",
            },
        ]
    )

    return {
        "story_brief": story_brief,
        "character_roster": character_roster,
        "world_context": world_context,
        "current_stage": "outlining",
    }
