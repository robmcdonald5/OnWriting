"""LLM-as-judge for pairwise A/B evaluation.

Presents both outputs in randomized order to prevent position bias.
Scores on the same 5 dimensions used by the Style Editor (1-4 scale).
Supports bidirectional evaluation for consensus-based verdicts.
"""

import logging
import random
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ai_writer.fine_tuning.comparison.schemas import JudgeVerdict
from ai_writer.fine_tuning.llm import get_openrouter_structured_llm

logger = logging.getLogger("ai_writer.fine_tuning.comparison.judge")


class JudgeOutput(BaseModel):
    """Structured output from the judge LLM."""

    reasoning: str = Field(description="Detailed comparison reasoning before scoring")
    style_adherence_a: int = Field(ge=1, le=4)
    style_adherence_b: int = Field(ge=1, le=4)
    character_voice_a: int = Field(ge=1, le=4)
    character_voice_b: int = Field(ge=1, le=4)
    outline_adherence_a: int = Field(ge=1, le=4)
    outline_adherence_b: int = Field(ge=1, le=4)
    pacing_a: int = Field(ge=1, le=4)
    pacing_b: int = Field(ge=1, le=4)
    prose_quality_a: int = Field(ge=1, le=4)
    prose_quality_b: int = Field(ge=1, le=4)
    preferred: Literal["A", "B", "tie"] = Field(
        description="Which output is better overall: 'A', 'B', or 'tie'"
    )


_JUDGE_SYSTEM_PROMPT = """\
You are an expert literary critic evaluating two creative writing outputs \
written in response to the same prompt. You will see Output A and Output B. \
Evaluate each on these 5 dimensions using a 1-4 scale:

1. **Style Adherence** (1-4): How well does the prose match the requested \
tone, style, and constraints?
2. **Character Voice** (1-4): Are characters distinct, authentic, and \
internally consistent?
3. **Outline Adherence** (1-4): Does the output follow the scene outline / \
prompt requirements?
4. **Pacing** (1-4): Is the prose well-paced with varied sentence structure \
and rhythm?
5. **Prose Quality** (1-4): Is the writing vivid, specific, and free of \
cliches and AI-typical constructions?

Score Guide:
- 4: Exceptional — publishable quality, no issues
- 3: Good — competent with minor issues
- 2: Adequate — noticeable problems
- 1: Poor — significant issues

IMPORTANT: First write detailed reasoning comparing both outputs, then \
assign scores. State your overall preference: A, B, or tie.\
"""

_DIMENSIONS = [
    "style_adherence",
    "character_voice",
    "outline_adherence",
    "pacing",
    "prose_quality",
]


class PairwiseJudge:
    """LLM-as-judge for A/B comparison."""

    def __init__(
        self,
        model: str = "anthropic/claude-sonnet-4-6",
        mock_mode: bool | None = None,
    ):
        self.model = model
        from ai_writer.config import get_settings

        settings = get_settings()
        self.mock_mode = (
            mock_mode if mock_mode is not None else settings.fine_tuning_mock_mode
        )

    def evaluate(
        self,
        prompt_id: str,
        prompt_text: str,
        base_text: str,
        tuned_text: str,
        force_a_is_base: bool | None = None,
    ) -> JudgeVerdict:
        """Evaluate a pair of outputs.

        Args:
            prompt_id: Identifier for the prompt.
            prompt_text: The original prompt.
            base_text: Base model output.
            tuned_text: Tuned model output.
            force_a_is_base: If provided, forces A/B ordering.
                True = A is base, False = A is tuned, None = random.

        Returns:
            JudgeVerdict with scores and preference.
        """
        if force_a_is_base is not None:
            a_is_base = force_a_is_base
        else:
            a_is_base = random.random() < 0.5

        if a_is_base:
            text_a, text_b = base_text, tuned_text
        else:
            text_a, text_b = tuned_text, base_text

        if self.mock_mode:
            return self._mock_evaluate(prompt_id, a_is_base)

        return self._real_evaluate(prompt_id, prompt_text, text_a, text_b, a_is_base)

    def evaluate_bidirectional(
        self,
        prompt_id: str,
        prompt_text: str,
        base_text: str,
        tuned_text: str,
    ) -> JudgeVerdict:
        """Run evaluation in both orderings and compute consensus.

        - Both agree on same winner -> that winner (confident)
        - Disagreement -> tie (position-sensitive, can't trust)

        Dimension scores are averaged from both orderings.
        """
        verdict_ab = self.evaluate(
            prompt_id, prompt_text, base_text, tuned_text, force_a_is_base=True
        )
        verdict_ba = self.evaluate(
            prompt_id, prompt_text, base_text, tuned_text, force_a_is_base=False
        )

        # De-randomize: convert both verdicts to base_preferred/tuned_preferred
        pref_ab = self._to_canonical(verdict_ab)
        pref_ba = self._to_canonical(verdict_ba)

        agreed = pref_ab == pref_ba
        consensus = pref_ab if agreed else "tie"

        # Average dimension scores (normalized to base=a perspective)
        scores_ab = self._get_base_tuned_scores(verdict_ab)
        scores_ba = self._get_base_tuned_scores(verdict_ba)

        avg_base = {}
        avg_tuned = {}
        for dim in _DIMENSIONS:
            avg_base[dim] = round((scores_ab["base"][dim] + scores_ba["base"][dim]) / 2)
            avg_tuned[dim] = round(
                (scores_ab["tuned"][dim] + scores_ba["tuned"][dim]) / 2
            )
            # Clamp to 1-4
            avg_base[dim] = max(1, min(4, avg_base[dim]))
            avg_tuned[dim] = max(1, min(4, avg_tuned[dim]))

        # Map consensus back to A/B (using a_is_base=True convention for output)
        preferred: Literal["A", "B", "tie"]
        if consensus == "base":
            preferred = "A"
        elif consensus == "tuned":
            preferred = "B"
        else:
            preferred = "tie"

        reasoning_parts = [
            f"[BIDIRECTIONAL] A=base ordering: {verdict_ab.preferred} | "
            f"A=tuned ordering: {verdict_ba.preferred} | "
            f"Position agreed: {'Yes' if agreed else 'No'}",
            f"--- Pass 1 (A=base) ---\n{verdict_ab.reasoning}",
            f"--- Pass 2 (A=tuned) ---\n{verdict_ba.reasoning}",
        ]

        return JudgeVerdict(
            prompt_id=prompt_id,
            style_adherence_a=avg_base["style_adherence"],
            style_adherence_b=avg_tuned["style_adherence"],
            character_voice_a=avg_base["character_voice"],
            character_voice_b=avg_tuned["character_voice"],
            outline_adherence_a=avg_base["outline_adherence"],
            outline_adherence_b=avg_tuned["outline_adherence"],
            pacing_a=avg_base["pacing"],
            pacing_b=avg_tuned["pacing"],
            prose_quality_a=avg_base["prose_quality"],
            prose_quality_b=avg_tuned["prose_quality"],
            preferred=preferred,
            reasoning="\n\n".join(reasoning_parts),
            a_is_base=True,
            is_bidirectional=True,
            position_agreed=agreed,
        )

    @staticmethod
    def _to_canonical(verdict: JudgeVerdict) -> str:
        """Convert A/B preference to base/tuned/tie."""
        if verdict.preferred == "tie":
            return "tie"
        if verdict.a_is_base:
            return "base" if verdict.preferred == "A" else "tuned"
        else:
            return "tuned" if verdict.preferred == "A" else "base"

    @staticmethod
    def _get_base_tuned_scores(verdict: JudgeVerdict) -> dict[str, dict[str, int]]:
        """Extract dimension scores normalized to base/tuned keys."""
        result: dict[str, dict[str, int]] = {"base": {}, "tuned": {}}
        for dim in _DIMENSIONS:
            score_a = getattr(verdict, f"{dim}_a")
            score_b = getattr(verdict, f"{dim}_b")
            if verdict.a_is_base:
                result["base"][dim] = score_a
                result["tuned"][dim] = score_b
            else:
                result["base"][dim] = score_b
                result["tuned"][dim] = score_a
        return result

    def _mock_evaluate(self, prompt_id: str, a_is_base: bool) -> JudgeVerdict:
        """Return synthetic judge verdict."""
        logger.info("[MOCK] Judge evaluating prompt: %s", prompt_id)
        return JudgeVerdict(
            prompt_id=prompt_id,
            style_adherence_a=3,
            style_adherence_b=3,
            character_voice_a=3,
            character_voice_b=3,
            outline_adherence_a=3,
            outline_adherence_b=3,
            pacing_a=3,
            pacing_b=3,
            prose_quality_a=3,
            prose_quality_b=3,
            preferred="tie",
            reasoning="[MOCK] Both outputs demonstrate competent prose.",
            a_is_base=a_is_base,
        )

    def _real_evaluate(
        self,
        prompt_id: str,
        prompt_text: str,
        text_a: str,
        text_b: str,
        a_is_base: bool,
    ) -> JudgeVerdict:
        """Run real LLM-as-judge evaluation."""
        user_content = (
            f"## Original Prompt\n{prompt_text}\n\n"
            f"## Output A\n{text_a}\n\n"
            f"## Output B\n{text_b}"
        )

        structured_llm = get_openrouter_structured_llm(
            JudgeOutput,
            model=self.model,
            temperature=0.1,
        )

        messages = [
            SystemMessage(content=_JUDGE_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]

        result = structured_llm.invoke(messages)

        return JudgeVerdict(
            prompt_id=prompt_id,
            style_adherence_a=result.style_adherence_a,
            style_adherence_b=result.style_adherence_b,
            character_voice_a=result.character_voice_a,
            character_voice_b=result.character_voice_b,
            outline_adherence_a=result.outline_adherence_a,
            outline_adherence_b=result.outline_adherence_b,
            pacing_a=result.pacing_a,
            pacing_b=result.pacing_b,
            prose_quality_a=result.prose_quality_a,
            prose_quality_b=result.prose_quality_b,
            preferred=result.preferred,
            reasoning=result.reasoning,
            a_is_base=a_is_base,
        )
