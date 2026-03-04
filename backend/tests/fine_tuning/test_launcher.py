"""Tests for the fine-tuning job launcher."""

from ai_writer.fine_tuning.config import FineTuningJobConfig
from ai_writer.fine_tuning.jobs.launcher import FineTuningLauncher


class TestFineTuningLauncher:
    def test_mock_launch(self):
        launcher = FineTuningLauncher(mock_mode=True)
        config = FineTuningJobConfig(
            training_data_uri="gs://test-bucket/data.jsonl",
            display_name="test-job",
        )
        result = launcher.launch(config)

        assert result.is_mock
        assert result.state == "JOB_STATE_RUNNING"
        assert result.display_name == "test-job"
        assert "mock" in result.job_name.lower() or "tuningJobs" in result.job_name
        assert result.tuned_model_endpoint != ""
        assert result.create_time != ""

    def test_mock_launch_custom_config(self):
        launcher = FineTuningLauncher(mock_mode=True)
        config = FineTuningJobConfig(
            source_model="gemini-2.5-flash",
            training_data_uri="gs://bucket/path.jsonl",
            display_name="custom-job",
            epochs=8,
            adapter_size=16,
            learning_rate_multiplier=0.5,
        )
        result = launcher.launch(config)
        assert result.is_mock
        assert result.display_name == "custom-job"
