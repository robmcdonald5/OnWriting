"""Tests for the A/B comparison runner."""

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from ai_writer.fine_tuning.comparison.runner import ComparisonRunner
from ai_writer.fine_tuning.config import ComparisonConfig


class TestComparisonRunner:
    """Test ComparisonRunner in mock mode."""

    def _make_runner(self, categories=None):
        config = ComparisonConfig(categories=categories or ["all"])
        return ComparisonRunner(config=config)

    @patch("ai_writer.fine_tuning.comparison.runner.get_settings")
    @patch("ai_writer.fine_tuning.comparison.runner.invoke")
    @patch("ai_writer.fine_tuning.comparison.runner.get_llm")
    def test_run_mock_no_judge(self, mock_get_llm, mock_invoke, mock_settings):
        """Full pipeline run in mock mode without judge."""
        settings = MagicMock()
        settings.fine_tuning_mock_mode = True
        settings.google_api_key = "test"
        settings.default_model = "gemini-2.5-flash"
        settings.default_temperature = 0.7
        mock_settings.return_value = settings

        mock_invoke.return_value = AIMessage(
            content="The old house creaked in the wind. Paint flaked from the shutters."
        )

        runner = self._make_runner(categories=["scene_writing"])
        report = runner.run(with_judge=False)

        assert report.prompt_count == 3
        assert report.is_mock
        assert len(report.results) == 3

        for result in report.results:
            assert result.prompt_category == "scene_writing"
            assert result.base_output.text != ""
            assert result.tuned_output.text != ""
            assert result.base_analysis.word_count > 0
            assert result.tuned_analysis.word_count > 0
            assert result.judge_verdict is None

    @patch("ai_writer.fine_tuning.comparison.runner.get_settings")
    @patch("ai_writer.fine_tuning.comparison.runner.invoke")
    @patch("ai_writer.fine_tuning.comparison.runner.get_llm")
    def test_run_single_category(self, mock_get_llm, mock_invoke, mock_settings):
        """Test running with a single category."""
        settings = MagicMock()
        settings.fine_tuning_mock_mode = True
        settings.google_api_key = "test"
        settings.default_model = "gemini-2.5-flash"
        settings.default_temperature = 0.7
        mock_settings.return_value = settings

        mock_invoke.return_value = AIMessage(content="Test prose output.")

        runner = self._make_runner(categories=["opening"])
        report = runner.run(with_judge=False)

        assert report.prompt_count == 2
        for r in report.results:
            assert r.prompt_category == "opening"

    @patch("ai_writer.fine_tuning.comparison.runner.get_settings")
    @patch("ai_writer.fine_tuning.comparison.runner.invoke")
    @patch("ai_writer.fine_tuning.comparison.runner.get_llm")
    def test_analysis_runs_on_outputs(self, mock_get_llm, mock_invoke, mock_settings):
        """Verify text analysis produces real metrics."""
        settings = MagicMock()
        settings.fine_tuning_mock_mode = True
        settings.google_api_key = "test"
        settings.default_model = "gemini-2.5-flash"
        settings.default_temperature = 0.7
        mock_settings.return_value = settings

        sample_prose = (
            "The corridor stretched ahead, narrow and low-ceilinged. "
            "Fluorescent tubes buzzed overhead. She stopped at the second door. "
            "The number had been painted over but she could still read it."
        )
        mock_invoke.return_value = AIMessage(content=sample_prose)

        runner = self._make_runner(categories=["opening"])
        report = runner.run(with_judge=False)

        analysis = report.results[0].base_analysis
        assert analysis.word_count > 0
        assert 0.0 <= analysis.slop_ratio <= 1.0

    @patch("ai_writer.fine_tuning.comparison.runner.get_settings")
    @patch("ai_writer.fine_tuning.comparison.runner.invoke")
    @patch("ai_writer.fine_tuning.comparison.runner.get_llm")
    def test_report_aggregate_stats(self, mock_get_llm, mock_invoke, mock_settings):
        """Test that aggregate stats are computed."""
        settings = MagicMock()
        settings.fine_tuning_mock_mode = True
        settings.google_api_key = "test"
        settings.default_model = "gemini-2.5-flash"
        settings.default_temperature = 0.7
        mock_settings.return_value = settings

        mock_invoke.return_value = AIMessage(content="Short test prose.")

        runner = self._make_runner(categories=["opening"])
        report = runner.run(with_judge=False)

        # Without judge, no wins/ties
        assert report.base_wins == 0
        assert report.tuned_wins == 0
        assert report.ties == 0
        # Metric deltas should be computed
        assert isinstance(report.mean_slop_delta, float)
        assert isinstance(report.mean_mtld_delta, float)
