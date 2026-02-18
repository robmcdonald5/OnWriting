"""Style Editor agent — three-layer rubric-based scene evaluation.

Layer 1: Deterministic checks (zero LLM cost) — word count, tense, slop.
Layer 2: Multi-dimensional LLM evaluation (1 structured call) — 5 dimensions at 1-3.
Layer 3: Algorithmic composite score (Python) — weighted average + floor check.

Uses low temperature (0.1) for deterministic evaluation per LLM-as-judge research.
"""

from ai_writer.agents.base import get_structured_llm, invoke
from ai_writer.schemas.editing import (
    EditFeedback,
    SceneRubric,
    StyleEditorOutput,
)
from ai_writer.utils.text_analysis import (
    check_tense_consistency,
    check_word_count,
    compute_slop_score,
)

STYLE_EDITOR_SYSTEM = """You are a Style Editor for a creative writing system.
Evaluate the scene prose against the outline using the rubric below.

## Evaluation Process

For EACH dimension, you MUST:
1. Cite 2-3 specific phrases from the text as evidence
2. Explain how they support your score
3. Then assign your 1-3 score

A first draft typically scores 1-2 on most dimensions. Score 3 only for genuinely excellent execution.

## Rubric (1-3 scale)

### Style Adherence
- 1 (Low): Prose contradicts 2+ tone axes (formality={formality}, darkness={darkness}, humor={humor}, pacing={pacing})
- 2 (Medium): Matches most tone axes, minor mismatches
- 3 (High): All tone axes reflected naturally in prose

### Character Voice
- 1 (Low): Characters sound interchangeable, generic dialogue
- 2 (Medium): Some distinction between characters, occasional drift
- 3 (High): Each character unmistakably voiced per their voice_notes

### Outline Adherence
- 1 (Low): Missing opening_hook OR closing_image OR >1 dialogue beat
- 2 (Medium): All structural elements present, minor deviations from outline
- 3 (High): opening_hook, closing_image, and all key_dialogue_beats executed precisely

### Pacing
- 1 (Low): Monotonous rhythm, no sentence variety, flat emotional arc
- 2 (Medium): Some rhythm variation, emotional arc partially achieved
- 3 (High): Dynamic sentence lengths serving emotional beats, arc fully realized

### Prose Quality
- 1 (Low): Heavy AI-isms (delve, tapestry, testament to, etc.), telling over showing
- 2 (Medium): Mostly clean prose, some generic phrasing
- 3 (High): Vivid, specific language; show-don't-tell throughout; original imagery

## Important Notes
- Flag any overused AI phrases (delve, tapestry, testament to, myriad, embark, navigate, multifaceted, pivotal, gossamer, iridescent, luminous, etc.) under prose_quality
- If prose_quality has AI-isms, it cannot score above 2
- Write revision_instructions ONLY if quality is insufficient — focus on the lowest-scoring dimensions
- In revision_instructions, be specific: quote the problematic text and suggest concrete improvements"""

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

    # ── Layer 2: LLM evaluation (1 structured call) ──

    system_prompt = STYLE_EDITOR_SYSTEM.format(
        formality=tone.formality,
        darkness=tone.darkness,
        humor=tone.humor,
        pacing=tone.pacing,
    )

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
