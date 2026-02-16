"""Scene Writer agent — writes prose for a single scene.

Takes the current scene outline and relevant context, produces a SceneDraft.
If revision_count > 0, incorporates editor feedback.
"""

from ai_writer.agents.base import get_llm
from ai_writer.config import get_settings
from ai_writer.schemas.writing import SceneDraft

SCENE_WRITER_SYSTEM = """You are a Scene Writer for a creative writing system.
Write the prose for the given scene based on the detailed outline provided.

Guidelines:
- Follow the scene outline EXACTLY — do not invent new plot points
- Match the tone_profile: formality={formality}, darkness={darkness}, humor={humor}, pacing={pacing}
- If prose_style is specified, match it: {prose_style}
- Write from the POV character's perspective
- Use the opening_hook to start the scene
- Use the closing_image to end the scene
- Hit the key_dialogue_beats naturally within the prose
- Follow the emotional_arc described in the outline
- Keep each character's voice consistent with their voice_notes and speech_patterns
- Target approximately {target_word_count} words
- Write complete, polished prose — not notes or outlines

Output ONLY the scene prose. No headers, no meta-commentary."""

REVISION_ADDENDUM = """

## REVISION INSTRUCTIONS
This is revision #{revision_count}. The editor provided this feedback:

{revision_instructions}

Address the editor's concerns while preserving what works. Focus on the specific
issues mentioned."""


def _get_scene_and_characters(state: dict):
    """Extract the current scene outline and relevant character profiles."""
    story_outline = state["story_outline"]
    character_roster = state["character_roster"]
    current_idx = state["current_scene_index"]

    # Flatten all scenes across acts
    all_scenes = []
    for act in story_outline.acts:
        all_scenes.extend(act.scenes)

    scene_outline = all_scenes[current_idx]

    # Gather character profiles for characters in this scene
    character_profiles = []
    for cid in scene_outline.characters_present:
        char = character_roster.get_character(cid)
        if char:
            character_profiles.append(char)

    return scene_outline, character_profiles


def run_scene_writer(state: dict) -> dict:
    """Execute the Scene Writer: scene outline + context → SceneDraft."""
    settings = get_settings()
    temp = settings.default_temperature

    scene_outline, characters = _get_scene_and_characters(state)
    story_brief = state["story_brief"]
    tone = story_brief.tone_profile

    # Build the system prompt with tone parameters
    system_prompt = SCENE_WRITER_SYSTEM.format(
        formality=tone.formality,
        darkness=tone.darkness,
        humor=tone.humor,
        pacing=tone.pacing,
        prose_style=tone.prose_style or "natural and engaging",
        target_word_count=scene_outline.target_word_count,
    )

    # Build scene context
    scene_context = (
        f"## Scene Outline\n{scene_outline.model_dump_json(indent=2)}\n\n"
        f"## Characters in Scene\n"
    )
    for char in characters:
        scene_context += f"### {char.name} ({char.role.value})\n"
        scene_context += f"Voice: {char.voice_notes}\n"
        scene_context += f"Patterns: {', '.join(char.speech_patterns)}\n"
        scene_context += f"Motivation: {char.motivation}\n\n"

    # Add revision context if this is a rewrite
    revision_count = state.get("revision_count", 0)
    if revision_count > 0:
        edit_feedback = state.get("edit_feedback", [])
        if edit_feedback:
            latest_feedback = edit_feedback[-1]
            system_prompt += REVISION_ADDENDUM.format(
                revision_count=revision_count,
                revision_instructions=latest_feedback.revision_instructions,
            )

    llm = get_llm(temperature=temp)
    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Write the scene:\n\n{scene_context}"},
        ]
    )

    prose = str(response.content)
    word_count = len(prose.split())

    scene_draft = SceneDraft(
        scene_id=scene_outline.scene_id,
        act_number=scene_outline.act_number,
        scene_number=scene_outline.scene_number,
        prose=prose,
        word_count=word_count,
        characters_used=[c.character_id for c in characters],
        scene_summary=f"Scene {scene_outline.scene_number}: {scene_outline.scene_goal}",
    )

    # Replace last draft if revising, otherwise append
    scene_drafts = list(state.get("scene_drafts", []))
    if revision_count > 0 and scene_drafts:
        scene_drafts[-1] = scene_draft
    else:
        scene_drafts.append(scene_draft)

    return {"scene_drafts": scene_drafts}
