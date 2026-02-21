"""Scene Writer agent — writes prose for a single scene.

Takes the current scene outline and relevant context, produces a SceneDraft.
If revision_count > 0, incorporates editor feedback.
"""

import logging

from ai_writer.agents.base import get_llm, invoke
from ai_writer.config import get_settings
from ai_writer.prompts.builders import build_scene_writer_prompt
from ai_writer.prompts.components import POLISH_ADDENDUM, REVISION_ADDENDUM
from ai_writer.prompts.configs import SceneWriterPromptConfig
from ai_writer.schemas.writing import SceneDraft

logger = logging.getLogger("ai_writer.agents.scene_writer")


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

    # Build config — start from state config, override with runtime tone values
    configs = state.get("prompt_configs", {})
    base_config = configs.get("scene_writer", SceneWriterPromptConfig())
    config = base_config.model_copy(
        update={
            "formality": tone.formality,
            "darkness": tone.darkness,
            "humor": tone.humor,
            "pacing": tone.pacing,
            "prose_style": tone.prose_style or base_config.prose_style,
            "target_word_count": scene_outline.target_word_count,
        }
    )

    system_prompt = build_scene_writer_prompt(config)

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
            rubric = latest_feedback.rubric

            # Build dimension breakdown
            dimension_breakdown = rubric.dimension_summary()

            # Identify critical and weak dimensions for focus
            focus_lines = []
            dims = {
                "style_adherence": rubric.style_adherence,
                "character_voice": rubric.character_voice,
                "outline_adherence": rubric.outline_adherence,
                "pacing": rubric.pacing,
                "prose_quality": rubric.prose_quality,
            }
            for dim_name, score in dims.items():
                if score <= 1:
                    focus_lines.append(
                        f"- {dim_name} (scored {score}/4) — CRITICAL, must improve"
                    )
                elif score == 2:
                    focus_lines.append(
                        f"- {dim_name} (scored 2/4) — significant weakness"
                    )
                elif score == 3:
                    focus_lines.append(
                        f"- {dim_name} (scored 3/4) — room for improvement"
                    )

            focus_text = ""
            if focus_lines:
                focus_text = "### Focus Your Revision On\n" + "\n".join(focus_lines)

            # Build confirmed slop section
            confirmed_slop = getattr(latest_feedback, "confirmed_slop", [])
            if confirmed_slop:
                slop_lines = [f'- REPLACE: "{phrase}"' for phrase in confirmed_slop]
                confirmed_slop_section = "\n".join(slop_lines)
            else:
                confirmed_slop_section = "None identified."

            # Build structural issues section
            struct_issues = []
            if rubric.opener_monotony:
                struct_issues.append(
                    "VARY: Sentence openings are monotonous — vary your "
                    "sentence starters instead of starting most with pronouns"
                )
            if rubric.length_monotony:
                struct_issues.append(
                    "VARY: Sentence lengths are too uniform — mix short "
                    "punchy sentences with longer complex ones"
                )
            if rubric.passive_heavy:
                struct_issues.append(
                    "VARY: Too much passive voice — convert passive "
                    "constructions to active voice where possible"
                )
            if rubric.structural_monotony:
                struct_issues.append(
                    "VARY: Sentence structures are too simple and "
                    "uniform — vary your syntax patterns"
                )
            if rubric.low_diversity:
                struct_issues.append(
                    "VARY: Low lexical diversity — use more varied "
                    "vocabulary, avoid repeating the same words"
                )
            structural_issues_section = (
                "\n".join(f"- {s}" for s in struct_issues)
                if struct_issues
                else "None identified."
            )

            if latest_feedback.approved:
                system_prompt += POLISH_ADDENDUM.format(
                    quality_score=latest_feedback.quality_score,
                    dimension_breakdown=dimension_breakdown,
                    revision_instructions=latest_feedback.revision_instructions,
                    focus_dimensions=focus_text,
                    confirmed_slop_section=confirmed_slop_section,
                    structural_issues_section=structural_issues_section,
                )
            else:
                system_prompt += REVISION_ADDENDUM.format(
                    revision_count=revision_count,
                    dimension_breakdown=dimension_breakdown,
                    revision_instructions=latest_feedback.revision_instructions,
                    focus_dimensions=focus_text,
                    confirmed_slop_section=confirmed_slop_section,
                    structural_issues_section=structural_issues_section,
                )

    revision_label = f" (revision {revision_count})" if revision_count > 0 else ""
    logger.info("Writing scene %d%s...", scene_outline.scene_number, revision_label)

    llm = get_llm(temperature=temp)
    response = invoke(
        llm,
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Write the scene:\n\n{scene_context}"},
        ],
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

    logger.info("Scene %d done: %d words", scene_outline.scene_number, word_count)

    # Replace last draft if revising, otherwise append
    scene_drafts = list(state.get("scene_drafts", []))
    if revision_count > 0 and scene_drafts:
        scene_drafts[-1] = scene_draft
    else:
        scene_drafts.append(scene_draft)

    return {"scene_drafts": scene_drafts}
