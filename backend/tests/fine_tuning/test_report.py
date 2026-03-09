"""Tests for comparison report generation."""

import json
import tempfile
from datetime import datetime, timezone

from ai_writer.fine_tuning.comparison.report import ReportGenerator
from ai_writer.fine_tuning.comparison.schemas import (
    ComparisonReport,
    JudgeVerdict,
    ModelOutput,
    PromptComparisonResult,
    TextAnalysisSnapshot,
)


def _make_report() -> ComparisonReport:
    """Create a minimal test report."""
    base_output = ModelOutput(
        model_id="base-model",
        prompt_id="test_01",
        prompt_category="scene_writing",
        text="Base model wrote this prose.",
        latency_seconds=1.5,
        token_count_approx=6,
    )
    tuned_output = ModelOutput(
        model_id="tuned-model",
        prompt_id="test_01",
        prompt_category="scene_writing",
        text="Tuned model wrote this prose.",
        latency_seconds=1.2,
        token_count_approx=6,
        is_mock=True,
    )
    base_analysis = TextAnalysisSnapshot(
        slop_ratio=0.95,
        mtld=72.5,
        word_count=50,
    )
    tuned_analysis = TextAnalysisSnapshot(
        slop_ratio=0.98,
        mtld=85.3,
        word_count=55,
    )
    verdict = JudgeVerdict(
        prompt_id="test_01",
        style_adherence_a=3,
        style_adherence_b=4,
        character_voice_a=3,
        character_voice_b=3,
        outline_adherence_a=3,
        outline_adherence_b=3,
        pacing_a=3,
        pacing_b=3,
        prose_quality_a=3,
        prose_quality_b=4,
        preferred="B",
        reasoning="B shows stronger prose quality.",
        a_is_base=True,
    )
    result = PromptComparisonResult(
        prompt_id="test_01",
        prompt_category="scene_writing",
        prompt_text="Write a scene about a lighthouse.",
        base_output=base_output,
        tuned_output=tuned_output,
        base_analysis=base_analysis,
        tuned_analysis=tuned_analysis,
        judge_verdict=verdict,
    )

    return ComparisonReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        base_model="gemini-2.5-flash",
        tuned_model="tuned-v1",
        prompt_count=1,
        results=[result],
        base_wins=0,
        tuned_wins=1,
        ties=0,
        mean_slop_delta=0.03,
        mean_mtld_delta=12.8,
        mean_word_count_delta=5.0,
        is_mock=True,
    )


class TestReportGenerator:
    def test_generate_creates_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(output_dir=tmpdir)
            report = _make_report()
            paths = generator.generate(report)

            assert paths["text"].exists()
            assert paths["json"].exists()
            assert paths["text"].suffix == ".txt"
            assert paths["json"].suffix == ".json"

    def test_text_report_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(output_dir=tmpdir)
            report = _make_report()
            paths = generator.generate(report)

            text = paths["text"].read_text(encoding="utf-8")
            assert "COMPARISON REPORT" in text
            assert "Base wins" in text
            assert "Tuned wins" in text
            assert "test_01" in text
            assert "Base model wrote" in text
            assert "Tuned model wrote" in text
            assert "METRICS COMPARISON" in text
            assert "JUDGE VERDICT" in text

    def test_json_report_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(output_dir=tmpdir)
            report = _make_report()
            paths = generator.generate(report)

            data = json.loads(paths["json"].read_text(encoding="utf-8"))
            assert data["prompt_count"] == 1
            assert data["tuned_wins"] == 1
            assert len(data["results"]) == 1
            assert data["results"][0]["prompt_id"] == "test_01"

    def test_report_without_judge(self):
        """Test report generation when judge is None."""
        report = _make_report()
        report.results[0].judge_verdict = None
        report.base_wins = 0
        report.tuned_wins = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(output_dir=tmpdir)
            paths = generator.generate(report)

            text = paths["text"].read_text(encoding="utf-8")
            assert "JUDGE VERDICT" not in text
