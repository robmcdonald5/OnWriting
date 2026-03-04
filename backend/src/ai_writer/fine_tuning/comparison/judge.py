"""LLM-as-judge for pairwise A/B evaluation.

Presents both outputs in randomized order to prevent position bias.
Scores on the same 5 dimensions used by the Style Editor (1-4 scale).
"""

import logging
import random
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ai_writer.agents.base import get_structured_llm, invoke
from ai_writer.fine_tuning.comparison.schemas import JudgeVerdict

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


class PairwiseJudge:
    """LLM-as-judge for A/B comparison."""

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
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
    ) -> JudgeVerdict:
        """Evaluate a pair of outputs.

        Randomizes A/B assignment to prevent position bias.

        Args:
            prompt_id: Identifier for the prompt.
            prompt_text: The original prompt.
            base_text: Base model output.
            tuned_text: Tuned model output.

        Returns:
            JudgeVerdict with scores and preference.
        """
        a_is_base = random.random() < 0.5

        if a_is_base:
            text_a, text_b = base_text, tuned_text
        else:
            text_a, text_b = tuned_text, base_text

        if self.mock_mode:
            return self._mock_evaluate(prompt_id, a_is_base)

        return self._real_evaluate(prompt_id, prompt_text, text_a, text_b, a_is_base)

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

        structured_llm = get_structured_llm(
            JudgeOutput,
            temperature=0.1,
            model=self.model,
        )

        messages = [
            SystemMessage(content=_JUDGE_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ]

        result = invoke(structured_llm, messages)

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
