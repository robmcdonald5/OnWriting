"""Style Editor agent — three-layer rubric-based scene evaluation.

Layer 1: Deterministic checks (zero LLM cost) — word count, tense, slop.
Layer 2: Multi-dimensional LLM evaluation (1 structured call) — 5 dimensions at 1-3.
Layer 3: Algorithmic composite score (Python) — weighted average + floor check.

Uses low temperature (0.1) for deterministic evaluation per LLM-as-judge research.
"""

from ai_writer.agents.base import get_structured_llm, invoke
from ai_writer.prompts.builders import build_style_editor_prompt
from ai_writer.prompts.configs import (
    ProseStructureConfig,
    StyleEditorPromptConfig,
    VocabularyConfig,
)
from ai_writer.schemas.editing import (
    EditFeedback,
    SceneRubric,
    StyleEditorOutput,
)
from ai_writer.utils.text_analysis import (
    check_tense_consistency,
    check_word_count,
    compute_prose_structure,
    compute_slop_score,
    compute_vocabulary_metrics,
)

# Evaluation temperature — lower than creative agents for consistency
_EVAL_TEMPERATURE = 0.1


def run_style_editor(state: dict) -> dict:
    """Execute the Style Editor: three-layer rubric evaluation."""
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

    assert latest_draft.scene_id == scene_outline.scene_id, (
        f"Draft/outline mismatch: draft={latest_draft.scene_id} "
        f"outline={scene_outline.scene_id}"
    )

    prose = latest_draft.prose

    # ── Layer 1: Deterministic checks (zero LLM cost) ──

    wc_result = check_word_count(prose, scene_outline.target_word_count)
    tense_result = check_tense_consistency(prose)
    slop_result = compute_slop_score(prose)

    print(
        f"  [Style Editor] Deterministic checks for {latest_draft.scene_id}:",
        flush=True,
    )
    wc_status = "OK" if wc_result.within_tolerance else "OUT OF RANGE"
    print(
        f"    word_count: {wc_status} ({wc_result.actual}/{wc_result.target})",
        flush=True,
    )
    print(
        f"    tense: {tense_result.dominant_tense} "
        f"({'consistent' if tense_result.consistent else 'INCONSISTENT'})",
        flush=True,
    )
    print(f"    slop: {slop_result.slop_ratio:.2f}", flush=True)
    if slop_result.found_phrases:
        print(f"    slop phrases: {slop_result.found_phrases[:5]}", flush=True)

    # Structural analysis
    configs = state.get("prompt_configs", {})
    structure_config = configs.get("prose_structure", ProseStructureConfig())
    structure_result = compute_prose_structure(prose, structure_config)

    structure_flags = structure_result.summary_lines()
    if structure_flags:
        print("    structural flags:", flush=True)
        for flag in structure_flags:
            print(f"      - {flag}", flush=True)
    else:
        print("    structure: OK", flush=True)

    # Vocabulary analysis
    vocab_config = configs.get("vocabulary", VocabularyConfig())
    vocab_result = compute_vocabulary_metrics(prose, vocab_config)

    vocab_flags = vocab_result.summary_lines()
    if vocab_flags:
        print("    vocabulary flags:", flush=True)
        for flag in vocab_flags:
            print(f"      - {flag}", flush=True)
    else:
        print("    vocabulary: OK", flush=True)

    # ── Layer 2: LLM evaluation (1 structured call) ──

    # Build config — start from state config, override with runtime tone values
    base_config = configs.get("style_editor", StyleEditorPromptConfig())
    config = base_config.model_copy(
        update={
            "formality": tone.formality,
            "darkness": tone.darkness,
            "humor": tone.humor,
            "pacing": tone.pacing,
        }
    )

    system_prompt = build_style_editor_prompt(config)

    # Build evaluation context
    eval_context = (
        f"## Scene Outline\n{scene_outline.model_dump_json(indent=2)}\n\n"
        f"## Scene Prose ({latest_draft.word_count} words)\n{prose}\n\n"
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

    # Inject slop scan results as advisory context for the LLM
    if slop_result.found_phrases:
        eval_context += (
            "\n## Flagged Phrases (potential AI-isms)\n"
            "The following phrases were detected by automated scan. "
            "Judge whether each is appropriate in this story's context "
            "or a generic LLM-ism that weakens the prose:\n"
        )
        for phrase in slop_result.found_phrases:
            eval_context += f'- "{phrase}"\n'

    # Inject structural analysis as advisory context
    if structure_flags:
        eval_context += "\n## Structural Analysis (automated)\n"
        for flag in structure_flags:
            eval_context += f"- {flag}\n"

    # Inject vocabulary analysis as advisory context
    if vocab_flags:
        eval_context += "\n## Vocabulary Analysis (automated)\n"
        for flag in vocab_flags:
            eval_context += f"- {flag}\n"

    print(
        f"  [Style Editor] Evaluating scene {latest_draft.scene_id}...",
        flush=True,
    )

    feedback_llm = get_structured_llm(StyleEditorOutput, temperature=_EVAL_TEMPERATURE)
    raw_output = invoke(
        feedback_llm,
        [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Evaluate this scene:\n\n{eval_context}",
            },
        ],
    )
    llm_output: StyleEditorOutput = raw_output  # type: ignore[assignment]

    # ── Layer 3: Algorithmic composite score (Python) ──

    rubric = SceneRubric(
        # Deterministic
        word_count_in_range=wc_result.within_tolerance,
        tense_consistent=tense_result.consistent,
        slop_ratio=slop_result.slop_ratio,
        # Structural analysis (advisory)
        opener_monotony=structure_result.opener_monotony,
        length_monotony=structure_result.length_monotony,
        passive_heavy=structure_result.passive_heavy,
        structural_monotony=structure_result.structural_monotony,
        # Vocabulary analysis (advisory)
        low_diversity=vocab_result.low_diversity,
        vocabulary_basic=vocab_result.vocabulary_basic,
        # LLM dimensions
        style_adherence=llm_output.style_adherence,
        character_voice=llm_output.character_voice,
        outline_adherence=llm_output.outline_adherence,
        pacing=llm_output.pacing,
        prose_quality=llm_output.prose_quality,
        dimension_reasoning=llm_output.dimension_reasoning,
    )

    quality_score = rubric.compute_quality_score()
    approved = rubric.compute_approved()

    edit_feedback = EditFeedback(
        scene_id=latest_draft.scene_id,
        quality_score=quality_score,
        approved=approved,
        overall_assessment=llm_output.overall_assessment,
        revision_instructions=llm_output.revision_instructions,
        rubric=rubric,
    )

    status = "APPROVED" if approved else "NEEDS REVISION"
    print(
        f"  [Style Editor] Score: {quality_score:.2f} [{status}]",
        flush=True,
    )
    print(f"    {rubric.dimension_summary()}", flush=True)
    if rubric.has_critical_failure():
        print("    ** CRITICAL FAILURE on one or more dimensions **", flush=True)

    feedback_list = list(state.get("edit_feedback", []))
    feedback_list.append(edit_feedback)

    return {"edit_feedback": feedback_list}
