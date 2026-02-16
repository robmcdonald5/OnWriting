"""Style Editor agent — evaluates scene prose and provides structured feedback.

Uses planning_temperature (0.3) for analytical, consistent evaluation.
Returns EditFeedback with a quality_score gate for the revision loop.
"""

from ai_writer.agents.base import get_structured_llm
from ai_writer.config import get_settings
from ai_writer.schemas.editing import EditFeedback

STYLE_EDITOR_SYSTEM = """You are a Style Editor for a creative writing system.
Evaluate the scene prose against the outline and provide structured feedback.

Evaluation criteria:
1. **Style**: Does the prose match the tone_profile? (formality={formality}, darkness={darkness}, humor={humor}, pacing={pacing})
2. **Character Voice**: Do characters sound distinct and consistent with their voice_notes?
3. **Pacing**: Does the scene flow well and hit the emotional_arc?
4. **Clarity**: Is the prose clear and engaging?
5. **Continuity**: Does the scene follow the outline's opening_hook, closing_image, and key_dialogue_beats?
6. **Grammar**: Any grammatical issues?

Scoring guide:
- 0.0-0.3: Needs complete rewrite
- 0.3-0.5: Major issues, significant revision needed
- 0.5-0.7: Decent but needs revision on specific issues
- 0.7-0.85: Good, minor suggestions only
- 0.85-1.0: Excellent, publish-ready

Set approved=true if quality_score >= 0.7.
If not approved, provide clear revision_instructions focusing on the most impactful improvements.

Be fair but demanding. A prototype first draft scoring 0.6-0.75 is realistic."""


def run_style_editor(state: dict) -> dict:
    """Execute the Style Editor: SceneDraft + context → EditFeedback."""
    settings = get_settings()
    temp = settings.planning_temperature

    story_brief = state["story_brief"]
    tone = story_brief.tone_profile
    scene_drafts = state["scene_drafts"]
    latest_draft = scene_drafts[-1]

    # Get the matching scene outline
    story_outline = state["story_outline"]
    all_scenes = []
    for act in story_outline.acts:
        all_scenes.extend(act.scenes)

    current_idx = state["current_scene_index"]
    scene_outline = all_scenes[current_idx]

    system_prompt = STYLE_EDITOR_SYSTEM.format(
        formality=tone.formality,
        darkness=tone.darkness,
        humor=tone.humor,
        pacing=tone.pacing,
    )

    # Build evaluation context
    eval_context = (
        f"## Scene Outline\n{scene_outline.model_dump_json(indent=2)}\n\n"
        f"## Scene Prose ({latest_draft.word_count} words)\n{latest_draft.prose}\n\n"
        f"## Tone Profile\n{tone.model_dump_json(indent=2)}"
    )

    # Get character voice info
    character_roster = state["character_roster"]
    voice_info = "\n## Character Voices\n"
    for cid in latest_draft.characters_used:
        char = character_roster.get_character(cid)
        if char:
            voice_info += f"- {char.name}: {char.voice_notes}\n"
    eval_context += voice_info

    feedback_llm = get_structured_llm(EditFeedback, temperature=temp)
    raw_feedback = feedback_llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Evaluate this scene:\n\n{eval_context}",
            },
        ]
    )
    edit_feedback: EditFeedback = raw_feedback  # type: ignore[assignment]

    # Ensure scene_id is set correctly
    edit_feedback.scene_id = latest_draft.scene_id

    feedback_list = list(state.get("edit_feedback", []))
    feedback_list.append(edit_feedback)

    return {"edit_feedback": feedback_list}
