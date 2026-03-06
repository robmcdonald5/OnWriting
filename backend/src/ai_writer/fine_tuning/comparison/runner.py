"""A/B comparison runner — sends prompts to both models, analyzes outputs.

This is the main orchestrator for the comparison testbed. For each prompt:
1. Sends to base model (via Google GenAI API)
2. Sends to tuned model (via Vertex AI or mock)
3. Runs deterministic text analysis on both outputs
4. Optionally invokes LLM-as-judge for pairwise evaluation
   (supports bidirectional and multi-judge modes)
"""

import logging
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage

from ai_writer.agents.base import get_llm, invoke
from ai_writer.config import get_settings
from ai_writer.fine_tuning.comparison.judge import PairwiseJudge
from ai_writer.fine_tuning.comparison.prompts import TestPrompt, get_prompts
from ai_writer.fine_tuning.comparison.schemas import (
    ComparisonReport,
    JudgeVerdict,
    ModelOutput,
    MultiJudgeVerdict,
    PromptComparisonResult,
    TextAnalysisSnapshot,
)
from ai_writer.fine_tuning.config import ComparisonConfig
from ai_writer.fine_tuning.llm import get_vertex_llm

logger = logging.getLogger("ai_writer.fine_tuning.comparison.runner")


class ComparisonRunner:
    """Run A/B comparisons between base and tuned models."""

    def __init__(self, config: ComparisonConfig | None = None):
        self.config = config or ComparisonConfig()
        settings = get_settings()
        self.mock_mode = settings.fine_tuning_mock_mode

    def run(self, with_judge: bool = True) -> ComparisonReport:
        """Run the full comparison pipeline.

        Args:
            with_judge: Whether to run LLM-as-judge evaluation.

        Returns:
            ComparisonReport with all results.
        """
        prompts = get_prompts(self.config.categories)
        logger.info(
            "Running comparison: %d prompts, judge=%s, mock=%s",
            len(prompts),
            with_judge,
            self.mock_mode,
        )

        results = []
        judges = self._create_judges() if with_judge else []

        for prompt in prompts:
            result = self._compare_single(prompt, judges)
            results.append(result)

        report = self._build_report(results)
        logger.info(
            "Comparison complete: base_wins=%d, tuned_wins=%d, ties=%d",
            report.base_wins,
            report.tuned_wins,
            report.ties,
        )
        return report

    def _create_judges(self) -> list[PairwiseJudge]:
        """Create judge instances for primary + additional models."""
        judges = [PairwiseJudge(model=self.config.judge_model)]
        for model in self.config.judge_models:
            judges.append(PairwiseJudge(model=model))
        return judges

    def _compare_single(
        self,
        prompt: TestPrompt,
        judges: list[PairwiseJudge],
    ) -> PromptComparisonResult:
        """Compare a single prompt across both models."""
        logger.info("Comparing prompt: %s (%s)", prompt.id, prompt.category)

        base_output = self._invoke_base(prompt)
        tuned_output = self._invoke_tuned(prompt)

        base_analysis = self._analyze(base_output.text)
        tuned_analysis = self._analyze(tuned_output.text)

        verdict = None
        multi_verdict = None

        if judges:
            verdicts = self._run_judges(
                judges,
                prompt.id,
                prompt.user_prompt,
                base_output.text,
                tuned_output.text,
            )

            if len(verdicts) == 1:
                verdict = verdicts[0]
            else:
                judge_models = [self.config.judge_model] + list(
                    self.config.judge_models
                )
                multi_verdict = self._aggregate_verdicts(verdicts, judge_models)
                verdict = verdicts[0]

        return PromptComparisonResult(
            prompt_id=prompt.id,
            prompt_category=prompt.category,
            prompt_text=prompt.user_prompt,
            system_prompt=prompt.system_prompt,
            base_output=base_output,
            tuned_output=tuned_output,
            base_analysis=base_analysis,
            tuned_analysis=tuned_analysis,
            judge_verdict=verdict,
            multi_judge_verdict=multi_verdict,
        )

    def _run_judges(
        self,
        judges: list[PairwiseJudge],
        prompt_id: str,
        prompt_text: str,
        base_text: str,
        tuned_text: str,
    ) -> list[JudgeVerdict]:
        """Run all judges, using bidirectional if configured."""
        verdicts = []
        for judge in judges:
            if self.config.bidirectional_judge:
                v = judge.evaluate_bidirectional(
                    prompt_id,
                    prompt_text,
                    base_text,
                    tuned_text,
                )
            else:
                v = judge.evaluate(
                    prompt_id=prompt_id,
                    prompt_text=prompt_text,
                    base_text=base_text,
                    tuned_text=tuned_text,
                )
            verdicts.append(v)
        return verdicts

    @staticmethod
    def _aggregate_verdicts(
        verdicts: list[JudgeVerdict],
        judge_models: list[str],
    ) -> MultiJudgeVerdict:
        """Aggregate multiple judge verdicts via majority vote."""
        # Convert each verdict to canonical preference (base/tuned/tie)
        canonical = []
        for v in verdicts:
            canonical.append(PairwiseJudge._to_canonical(v))

        # Majority vote
        counts = Counter(canonical)
        winner = counts.most_common(1)[0][0]

        # Map back to A/B (using a_is_base=True convention)
        consensus: Literal["A", "B", "tie"]
        if winner == "base":
            consensus = "A"
        elif winner == "tuned":
            consensus = "B"
        else:
            consensus = "tie"

        agreement = counts[winner] / len(verdicts)

        return MultiJudgeVerdict(
            verdicts=verdicts,
            judge_models=judge_models,
            consensus_preferred=consensus,
            agreement_ratio=round(agreement, 2),
        )

    def _invoke_base(self, prompt: TestPrompt) -> ModelOutput:
        """Invoke the base model (or return mock output)."""
        if self.mock_mode:
            from ai_writer.fine_tuning.llm import _MOCK_CREATIVE_TEXT

            return ModelOutput(
                model_id=self.config.base_model,
                prompt_id=prompt.id,
                prompt_category=prompt.category,
                text=_MOCK_CREATIVE_TEXT,
                latency_seconds=0.0,
                token_count_approx=max(1, len(_MOCK_CREATIVE_TEXT) // 4),
                is_mock=True,
            )

        llm = get_llm(temperature=self.config.temperature)
        messages = [
            SystemMessage(content=prompt.system_prompt),
            HumanMessage(content=prompt.user_prompt),
        ]

        start = time.time()
        result = invoke(llm, messages)
        elapsed = time.time() - start

        text = result.content if hasattr(result, "content") else str(result)
        return ModelOutput(
            model_id=self.config.base_model,
            prompt_id=prompt.id,
            prompt_category=prompt.category,
            text=text,
            latency_seconds=round(elapsed, 2),
            token_count_approx=max(1, len(text) // 4),
            is_mock=False,
        )

    def _invoke_tuned(self, prompt: TestPrompt) -> ModelOutput:
        """Invoke the tuned model (or mock)."""
        llm = get_vertex_llm(
            model_endpoint=self.config.tuned_model_endpoint,
            temperature=self.config.temperature,
        )
        messages = [
            SystemMessage(content=prompt.system_prompt),
            HumanMessage(content=prompt.user_prompt),
        ]

        start = time.time()
        result = llm.invoke(messages)
        elapsed = time.time() - start

        text = result.content if hasattr(result, "content") else str(result)
        return ModelOutput(
            model_id=self.config.tuned_model_endpoint or "mock-tuned",
            prompt_id=prompt.id,
            prompt_category=prompt.category,
            text=text,
            latency_seconds=round(elapsed, 2),
            token_count_approx=max(1, len(text) // 4),
            is_mock=self.mock_mode,
        )

    def _analyze(self, text: str) -> TextAnalysisSnapshot:
        """Run deterministic text analysis on a prose output."""
        from ai_writer.utils.text_analysis import (
            compute_prose_structure,
            compute_slop_score,
            compute_vocabulary_metrics,
        )

        slop = compute_slop_score(text)
        vocab = compute_vocabulary_metrics(text)
        structure = compute_prose_structure(text)

        return TextAnalysisSnapshot(
            slop_ratio=slop.slop_ratio,
            slop_phrase_count=len(slop.raw_phrase_list),
            mtld=vocab.mtld,
            mattr=vocab.mattr,
            mean_word_zipf=vocab.avg_zipf_frequency,
            opener_monotony=structure.opener_monotony,
            top_opener_pos=structure.top_opener_pos,
            top_opener_ratio=structure.top_opener_ratio,
            length_monotony=structure.length_monotony,
            sent_length_cv=structure.sent_length_cv,
            passive_ratio=structure.passive_ratio,
            mean_dep_distance=structure.dep_distance_mean,
            word_count=len(text.split()),
        )

    def _build_report(self, results: list[PromptComparisonResult]) -> ComparisonReport:
        """Build aggregate report from individual results."""
        base_wins = 0
        tuned_wins = 0
        ties = 0
        slop_deltas = []
        mtld_deltas = []
        wc_deltas = []

        for r in results:
            preferred_source = self._get_effective_verdict(r)
            if preferred_source:
                if preferred_source == "base":
                    base_wins += 1
                elif preferred_source == "tuned":
                    tuned_wins += 1
                else:
                    ties += 1

            slop_deltas.append(r.tuned_analysis.slop_ratio - r.base_analysis.slop_ratio)
            mtld_deltas.append(r.tuned_analysis.mtld - r.base_analysis.mtld)
            wc_deltas.append(r.tuned_analysis.word_count - r.base_analysis.word_count)

        n = len(results) or 1
        settings = get_settings()

        return ComparisonReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            base_model=self.config.base_model,
            tuned_model=self.config.tuned_model_endpoint or "mock-tuned",
            prompt_count=len(results),
            results=results,
            base_wins=base_wins,
            tuned_wins=tuned_wins,
            ties=ties,
            mean_slop_delta=round(sum(slop_deltas) / n, 4),
            mean_mtld_delta=round(sum(mtld_deltas) / n, 2),
            mean_word_count_delta=round(sum(wc_deltas) / n, 1),
            is_mock=settings.fine_tuning_mock_mode,
        )

    @staticmethod
    def _get_effective_verdict(result: PromptComparisonResult) -> str | None:
        """Get the canonical winner from either multi-judge or single-judge verdict.

        Returns "base", "tuned", "tie", or None (no judge).
        """
        if result.multi_judge_verdict:
            pref = result.multi_judge_verdict.consensus_preferred
        elif result.judge_verdict:
            pref = result.judge_verdict.preferred
        else:
            return None

        if pref == "tie":
            return "tie"

        # Use judge_verdict for a_is_base mapping
        verdict = result.judge_verdict
        if verdict is None:
            return "tie"

        if verdict.a_is_base:
            return "base" if pref == "A" else "tuned"
        else:
            return "tuned" if pref == "A" else "base"
