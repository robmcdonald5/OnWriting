"""Style Editor agent — three-layer rubric-based scene evaluation.

Layer 1: Deterministic checks (zero LLM cost) — word count, tense, slop.
Layer 2: Multi-dimensional LLM evaluation (1 structured call) — 5 dimensions at 1-3.
Layer 3: Algorithmic composite score (Python) — weighted average + floor check.

Uses low temperature (0.1) for deterministic evaluation per LLM-as-judge research.
"""

import logging

from ai_writer.agents.base import get_structured_llm, invoke
from ai_writer.prompts.builders import build_style_editor_prompt
from ai_writer.prompts.configs import (
    ProseStructureConfig,
    ScoreCapConfig,
    SlopConfig,
    StyleEditorPromptConfig,
    VocabularyConfig,
)
from ai_writer.schemas.editing import (
    EditFeedback,
    SceneMetrics,
    SceneRubric,
    StyleEditorOutput,
)
from ai_writer.utils.text_analysis import (
    build_story_allowlist,
    check_tense_consistency,
    check_word_count,
    compute_prose_structure,
    compute_slop_score,
    compute_vocabulary_metrics,
    detect_cross_scene_repetition,
)

logger = logging.getLogger("ai_writer.agents.style_editor")

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
    configs = state.get("prompt_configs", {})

    # ── Layer 1: Deterministic checks (zero LLM cost) ──

    allowlist = build_story_allowlist(state)
    slop_config = configs.get("slop", SlopConfig())

    wc_result = check_word_count(prose, scene_outline.target_word_count)
    tense_result = check_tense_consistency(prose)
    slop_result = compute_slop_score(prose, allowlist=allowlist, config=slop_config)

    logger.info("Deterministic checks for %s:", latest_draft.scene_id)
    wc_status = "OK" if wc_result.within_tolerance else "OUT OF RANGE"
    logger.info(
        "  word_count: %s (%d/%d)", wc_status, wc_result.actual, wc_result.target
    )
    logger.info(
        "  tense: %s (%s)",
        tense_result.dominant_tense,
        "consistent" if tense_result.consistent else "INCONSISTENT",
    )
    logger.info("  slop: %.2f", slop_result.slop_ratio)
    if slop_result.found_phrases:
        logger.info("  slop phrases: %s", slop_result.found_phrases[:5])
    if slop_result.found_words:
        top_words = sorted(
            slop_result.found_words.items(), key=lambda x: x[1], reverse=True
        )[:5]
        logger.info("  slop words (excess): %s", top_words)

    # Structural analysis
    structure_config = configs.get("prose_structure", ProseStructureConfig())
    structure_result = compute_prose_structure(prose, structure_config)

    structure_flags = structure_result.summary_lines()
    if structure_flags:
        logger.info("  structural flags:")
        for flag in structure_flags:
            logger.info("    - %s", flag)
    else:
        logger.info("  structure: OK")

    # Vocabulary analysis
    vocab_config = configs.get("vocabulary", VocabularyConfig())
    vocab_result = compute_vocabulary_metrics(prose, vocab_config)

    vocab_flags = vocab_result.summary_lines()
    if vocab_flags:
        logger.info("  vocabulary flags:")
        for flag in vocab_flags:
            logger.info("    - %s", flag)
    else:
        logger.info("  vocabulary: OK")

    # Cross-scene repetition detection
    prior_proses = [d.prose for d in scene_drafts[:-1]]
    repetition_result = detect_cross_scene_repetition(prose, prior_proses)
    if repetition_result.repeated_count > 0:
        logger.info("  cross-scene repetitions: %d", repetition_result.repeated_count)

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
            eval_context += f"- {phrase}\n"

    if slop_result.found_words:
        eval_context += "\n## Overused Words (automated)\n"
        top_words = sorted(
            slop_result.found_words.items(), key=lambda x: x[1], reverse=True
        )[:10]
        for word, excess in top_words:
            eval_context += f'- "{word}" ({excess} excess occurrence(s))\n'

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

    # Inject cross-scene repetition
    if repetition_result.repeated_phrases:
        eval_context += "\n## Cross-Scene Repetitions (automated)\n"
        eval_context += (
            "These multi-word phrases appear in both this scene and prior scenes:\n"
        )
        for phrase in repetition_result.repeated_phrases:
            eval_context += f'- "{phrase}"\n'

    # ── Deterministic criteria pre-evaluation ──
    # Tell the LLM which atomic criteria already passed/failed
    eval_context += "\n## Pre-Evaluated Criteria (deterministic)\n"
    eval_context += "These criteria have been evaluated automatically. "
    eval_context += "You CANNOT override these results.\n\n"

    # Pacing criteria (a) and (b)
    pacing_cv_pass = (
        structure_result.sent_length_cv > structure_config.length_cv_threshold
    )
    pacing_opener_pass = not structure_result.opener_monotony
    eval_context += "### Pacing\n"
    eval_context += (
        f"(a) Sentence length variety (CV > {structure_config.length_cv_threshold}): "
        f"{'PASS' if pacing_cv_pass else 'FAIL'} "
        f"(CV = {structure_result.sent_length_cv:.2f})\n"
    )
    eval_context += (
        f"(b) Opener variety (no type > {structure_config.opener_monotony_threshold:.0%}): "
        f"{'PASS' if pacing_opener_pass else 'FAIL'} "
        f"(top opener = {structure_result.top_opener_ratio:.0%})\n"
    )

    # Prose Quality criteria (a) and (b)
    # Note: confirmed_slop count is determined after LLM call, so we
    # pre-evaluate based on the flagged phrases count as a proxy.
    # The actual cap is applied post-LLM via ScoreCapConfig.
    prose_slop_pass = not slop_result.found_phrases
    prose_vocab_pass = not vocab_result.vocabulary_basic
    eval_context += "\n### Prose Quality\n"
    eval_context += (
        f"(a) Zero confirmed AI-isms: "
        f"{'PASS (no phrases flagged)' if prose_slop_pass else 'PENDING — you must evaluate flagged phrases above'}\n"
    )
    eval_context += (
        f"(b) Vocabulary not basic: " f"{'PASS' if prose_vocab_pass else 'FAIL'}\n"
    )

    # Outline Adherence criterion (a)
    eval_context += "\n### Outline Adherence\n"
    eval_context += (
        f"(a) Word count within tolerance: "
        f"{'PASS' if wc_result.within_tolerance else 'FAIL'} "
        f"({wc_result.actual}/{wc_result.target} words)\n"
    )

    logger.info("Evaluating scene %s...", latest_draft.scene_id)

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

    # ── Deterministic score caps ──
    # Apply hard caps based on automated analysis. The LLM provides baseline
    # scores and reasoning, but Python enforces constraints the LLM may ignore.
    cap_config = configs.get("score_caps", ScoreCapConfig())

    capped_pacing = llm_output.pacing
    if structure_result.opener_monotony or structure_result.length_monotony:
        capped_pacing = min(capped_pacing, cap_config.cap_pacing_on_monotony)
        if capped_pacing < llm_output.pacing:
            logger.info(
                "Score cap: pacing %d -> %d (structural monotony)",
                llm_output.pacing,
                capped_pacing,
            )

    capped_prose = llm_output.prose_quality
    if len(llm_output.confirmed_slop) >= cap_config.cap_prose_on_slop_count:
        capped_prose = min(capped_prose, cap_config.cap_prose_on_slop_value)
        if capped_prose < llm_output.prose_quality:
            logger.info(
                "Score cap: prose_quality %d -> %d (%d confirmed AI-isms)",
                llm_output.prose_quality,
                capped_prose,
                len(llm_output.confirmed_slop),
            )
    if vocab_result.low_diversity:
        capped_prose = min(capped_prose, cap_config.cap_prose_on_low_diversity)
        if capped_prose < llm_output.prose_quality:
            logger.info(
                "Score cap: prose_quality %d -> %d (low vocabulary diversity)",
                llm_output.prose_quality,
                capped_prose,
            )

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
        # Cross-scene
        cross_scene_repetitions=repetition_result.repeated_count,
        # LLM dimensions (with deterministic caps applied)
        style_adherence=llm_output.style_adherence,
        character_voice=llm_output.character_voice,
        outline_adherence=llm_output.outline_adherence,
        pacing=capped_pacing,
        prose_quality=capped_prose,
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
        confirmed_slop=llm_output.confirmed_slop,
        rubric=rubric,
    )

    status = "APPROVED" if approved else "NEEDS REVISION"
    logger.info("Score: %.2f [%s]", quality_score, status)
    logger.info("  %s", rubric.dimension_summary())
    if rubric.has_critical_failure():
        logger.warning("CRITICAL FAILURE on one or more dimensions")

    # Record scene metrics for trend tracking
    metrics = SceneMetrics(
        scene_id=latest_draft.scene_id,
        slop_ratio=slop_result.slop_ratio,
        mtld=vocab_result.mtld,
        opener_ratio=structure_result.top_opener_ratio,
        sent_length_cv=structure_result.sent_length_cv,
        word_count=latest_draft.word_count,
    )
    scene_metrics = list(state.get("scene_metrics", []))

    # Trend warning: MTLD regression
    if scene_metrics:
        mean_mtld = sum(m.mtld for m in scene_metrics) / len(scene_metrics)
        if mean_mtld > 0 and metrics.mtld < mean_mtld * 0.8:
            logger.warning(
                "Quality regression: MTLD dropped from %.0f to %.0f",
                mean_mtld,
                metrics.mtld,
            )

    scene_metrics.append(metrics)

    feedback_list = list(state.get("edit_feedback", []))
    feedback_list.append(edit_feedback)

    return {"edit_feedback": feedback_list, "scene_metrics": scene_metrics}
