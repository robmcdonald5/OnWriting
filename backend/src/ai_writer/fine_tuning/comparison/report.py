"""Report generation for A/B comparison results.

Generates side-by-side reports with:
- Full prose outputs for manual review
- Per-prompt text analysis metrics
- Per-prompt judge verdicts
- Aggregate win/loss/tie and metric deltas
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from ai_writer.fine_tuning.comparison.schemas import (
    ComparisonReport,
    PromptComparisonResult,
)

logger = logging.getLogger("ai_writer.fine_tuning.comparison.report")


class ReportGenerator:
    """Generate comparison reports in text and JSON formats."""

    def __init__(self, output_dir: str = "output/comparisons"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, report: ComparisonReport) -> dict[str, Path]:
        """Generate both text and JSON reports.

        Returns:
            Dict with 'text' and 'json' keys pointing to output paths.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        prefix = f"comparison_{timestamp}"

        text_path = self._write_text_report(report, prefix)
        json_path = self._write_json_report(report, prefix)

        logger.info("Reports written: %s, %s", text_path, json_path)
        return {"text": text_path, "json": json_path}

    def _write_text_report(self, report: ComparisonReport, prefix: str) -> Path:
        """Write human-readable text report."""
        path = self.output_dir / f"{prefix}.txt"
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append("A/B COMPARISON REPORT")
        lines.append("=" * 80)
        lines.append(f"Timestamp:    {report.timestamp}")
        lines.append(f"Base model:   {report.base_model}")
        lines.append(f"Tuned model:  {report.tuned_model}")
        lines.append(f"Prompts:      {report.prompt_count}")
        lines.append(f"Mock mode:    {report.is_mock}")
        lines.append("")

        # Aggregate results
        lines.append("-" * 40)
        lines.append("AGGREGATE RESULTS")
        lines.append("-" * 40)
        lines.append(f"Base wins:    {report.base_wins}")
        lines.append(f"Tuned wins:   {report.tuned_wins}")
        lines.append(f"Ties:         {report.ties}")
        lines.append(f"Slop delta:   {report.mean_slop_delta:+.4f} (+ = tuned cleaner)")
        lines.append(
            f"MTLD delta:   {report.mean_mtld_delta:+.2f} (+ = tuned more diverse)"
        )
        lines.append(f"WC delta:     {report.mean_word_count_delta:+.1f}")
        lines.append("")

        # Per-prompt details
        for result in report.results:
            lines.extend(self._format_prompt_result(result))

        text = "\n".join(lines)
        path.write_text(text, encoding="utf-8")
        return path

    def _format_prompt_result(self, result: PromptComparisonResult) -> list[str]:
        """Format a single prompt comparison result."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"PROMPT: {result.prompt_id} ({result.prompt_category})")
        lines.append("=" * 80)
        prompt_display = result.prompt_text
        if len(prompt_display) > 200:
            prompt_display = prompt_display[:200] + "..."
        lines.append(f"Prompt: {prompt_display}")
        lines.append("")

        # Base output
        lines.append("--- BASE MODEL OUTPUT ---")
        lines.append(result.base_output.text)
        lines.append("")
        lines.append(f"  Latency: {result.base_output.latency_seconds}s")
        lines.append(f"  Tokens:  ~{result.base_output.token_count_approx}")
        lines.append("")

        # Tuned output
        lines.append("--- TUNED MODEL OUTPUT ---")
        lines.append(result.tuned_output.text)
        lines.append("")
        lines.append(f"  Latency: {result.tuned_output.latency_seconds}s")
        lines.append(f"  Tokens:  ~{result.tuned_output.token_count_approx}")
        lines.append("")

        # Metrics comparison
        lines.append("--- METRICS COMPARISON ---")
        ba = result.base_analysis
        ta = result.tuned_analysis
        lines.append(f"  {'Metric':<25} {'Base':>10} {'Tuned':>10} {'Delta':>10}")
        lines.append(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")
        lines.append(
            f"  {'Slop ratio':<25} {ba.slop_ratio:>10.4f} {ta.slop_ratio:>10.4f} "
            f"{ta.slop_ratio - ba.slop_ratio:>+10.4f}"
        )
        lines.append(
            f"  {'Slop phrases':<25} {ba.slop_phrase_count:>10d} {ta.slop_phrase_count:>10d} "
            f"{ta.slop_phrase_count - ba.slop_phrase_count:>+10d}"
        )
        lines.append(
            f"  {'MTLD':<25} {ba.mtld:>10.1f} {ta.mtld:>10.1f} "
            f"{ta.mtld - ba.mtld:>+10.1f}"
        )
        lines.append(
            f"  {'MATTR':<25} {ba.mattr:>10.4f} {ta.mattr:>10.4f} "
            f"{ta.mattr - ba.mattr:>+10.4f}"
        )
        lines.append(
            f"  {'Word count':<25} {ba.word_count:>10d} {ta.word_count:>10d} "
            f"{ta.word_count - ba.word_count:>+10d}"
        )
        lines.append(
            f"  {'Opener monotony':<25} {str(ba.opener_monotony):>10} {str(ta.opener_monotony):>10}"
        )
        lines.append(
            f"  {'Sent length CV':<25} {ba.sent_length_cv:>10.3f} {ta.sent_length_cv:>10.3f} "
            f"{ta.sent_length_cv - ba.sent_length_cv:>+10.3f}"
        )
        lines.append("")

        # Judge verdict
        if result.judge_verdict:
            v = result.judge_verdict
            label_a = "base" if v.a_is_base else "tuned"
            label_b = "tuned" if v.a_is_base else "base"
            lines.append("--- JUDGE VERDICT ---")
            lines.append(
                f"  Preferred: {v.preferred} ({label_a if v.preferred == 'A' else label_b if v.preferred == 'B' else 'tie'})"
            )
            lines.append(
                f"  {'Dimension':<25} {'A (' + label_a + ')':>10} {'B (' + label_b + ')':>10}"
            )
            lines.append(f"  {'-'*25} {'-'*10} {'-'*10}")
            lines.append(
                f"  {'Style adherence':<25} {v.style_adherence_a:>10} {v.style_adherence_b:>10}"
            )
            lines.append(
                f"  {'Character voice':<25} {v.character_voice_a:>10} {v.character_voice_b:>10}"
            )
            lines.append(
                f"  {'Outline adherence':<25} {v.outline_adherence_a:>10} {v.outline_adherence_b:>10}"
            )
            lines.append(f"  {'Pacing':<25} {v.pacing_a:>10} {v.pacing_b:>10}")
            lines.append(
                f"  {'Prose quality':<25} {v.prose_quality_a:>10} {v.prose_quality_b:>10}"
            )
            lines.append(f"  Reasoning: {v.reasoning}")
            lines.append("")

        return lines

    def _write_json_report(self, report: ComparisonReport, prefix: str) -> Path:
        """Write machine-readable JSON report."""
        path = self.output_dir / f"{prefix}.json"
        data = report.model_dump()
        path.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )
        return path
