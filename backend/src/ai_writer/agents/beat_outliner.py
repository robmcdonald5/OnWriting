"""Beat Outliner agent — breaks the story brief into narrative beats and scene outlines.

Single LLM call: StoryBrief + CharacterRoster + WorldContext → StoryOutline
"""

from ai_writer.agents.base import get_structured_llm
from ai_writer.config import get_settings
from ai_writer.schemas.structure import StoryOutline

BEAT_OUTLINER_SYSTEM = """You are a Beat Outliner for a creative writing system.
Given a StoryBrief, CharacterRoster, and WorldContext, create a detailed StoryOutline.

Guidelines:
- Create exactly the number of acts specified in scope.num_acts
- Create exactly the number of scenes per act specified in scope.scenes_per_act
- Every scene must have a unique scene_id (e.g. "s1", "s2", "s3")
- Every beat must have a unique beat_id (e.g. "b1", "b2", "b3")
- Assign beats to scenes via beat_ids
- Use beat_type values: hook, inciting_incident, rising_action, midpoint, complication, crisis, climax, falling_action, resolution
- Characters in characters_present and characters_involved must reference character_ids from the roster
- Locations must reference location_ids from the world context
- Write specific opening_hook and closing_image for each scene
- Include 2-4 key_dialogue_beats per scene describing important dialogue moments
- Set emotional_arc for each scene (e.g. "curiosity builds to dread")
- Set scene_goal to describe what the scene must accomplish
- The first scene's prior_scene_summary should be empty
- Each subsequent scene's prior_scene_summary should describe what happens in the previous scene(s)
- Set target_word_count per scene based on the scope parameters

Be extremely specific. Scene Writers should make ZERO plot decisions — everything
should be predetermined in this outline."""


def run_beat_outliner(state: dict) -> dict:
    """Execute the Beat Outliner: StoryBrief + CharacterRoster + WorldContext → StoryOutline."""
    settings = get_settings()
    temp = settings.planning_temperature

    story_brief = state["story_brief"]
    character_roster = state["character_roster"]
    world_context = state["world_context"]

    outline_llm = get_structured_llm(StoryOutline, temperature=temp)

    context = (
        f"## Story Brief\n{story_brief.model_dump_json(indent=2)}\n\n"
        f"## Character Roster\n{character_roster.model_dump_json(indent=2)}\n\n"
        f"## World Context\n{world_context.model_dump_json(indent=2)}"
    )

    story_outline = outline_llm.invoke(
        [
            {"role": "system", "content": BEAT_OUTLINER_SYSTEM},
            {
                "role": "user",
                "content": f"Create a detailed story outline:\n\n{context}",
            },
        ]
    )

    return {
        "story_outline": story_outline,
        "current_stage": "writing",
    }
