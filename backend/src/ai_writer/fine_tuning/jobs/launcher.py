"""Vertex AI SFT job launcher.

Launches supervised fine-tuning jobs on Vertex AI. In mock mode,
simulates the job launch and returns synthetic job metadata.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from ai_writer.config import get_settings
from ai_writer.fine_tuning.config import FineTuningJobConfig

logger = logging.getLogger("ai_writer.fine_tuning.jobs.launcher")


@dataclass
class TuningJobResult:
    """Result of launching a fine-tuning job."""

    job_name: str
    display_name: str
    state: str
    create_time: str
    tuned_model_endpoint: str
    is_mock: bool


class FineTuningLauncher:
    """Launch Vertex AI supervised fine-tuning jobs."""

    def __init__(self, mock_mode: bool | None = None):
        settings = get_settings()
        self.mock_mode = (
            mock_mode if mock_mode is not None else settings.fine_tuning_mock_mode
        )
        self.project_id = settings.vertex_project_id
        self.region = settings.vertex_region

    def launch(self, config: FineTuningJobConfig) -> TuningJobResult:
        """Launch an SFT job.

        Args:
            config: Fine-tuning job configuration.

        Returns:
            TuningJobResult with job metadata.
        """
        if self.mock_mode:
            return self._mock_launch(config)

        return self._real_launch(config)

    def _mock_launch(self, config: FineTuningJobConfig) -> TuningJobResult:
        """Simulate launching a tuning job."""
        now = datetime.now(timezone.utc).isoformat()
        job_name = f"projects/{self.project_id or 'mock-project'}/locations/{self.region}/tuningJobs/mock-{int(datetime.now(timezone.utc).timestamp())}"

        logger.info("[MOCK] Launched SFT job: %s", job_name)
        logger.info("[MOCK]   Model: %s", config.source_model)
        logger.info("[MOCK]   Data: %s", config.training_data_uri)
        logger.info(
            "[MOCK]   Epochs: %d, Adapter: %d", config.epochs, config.adapter_size
        )

        return TuningJobResult(
            job_name=job_name,
            display_name=config.display_name,
            state="JOB_STATE_RUNNING",
            create_time=now,
            tuned_model_endpoint="projects/mock-project/locations/us-central1/endpoints/mock-endpoint-123",
            is_mock=True,
        )

    def _real_launch(self, config: FineTuningJobConfig) -> TuningJobResult:
        """Launch a real Vertex AI tuning job."""
        if not config.training_data_uri:
            raise ValueError("training_data_uri is required")
        if not self.project_id:
            raise ValueError("vertex_project_id must be set")

        try:
            from google.cloud import aiplatform
        except ImportError as exc:
            raise ImportError(
                "google-cloud-aiplatform is required for real tuning jobs. "
                "Install with: poetry install --with fine-tuning"
            ) from exc

        aiplatform.init(project=self.project_id, location=self.region)

        sft_tuning_job = aiplatform.SupervisedTuningJob(
            source_model=config.source_model,
            train_dataset=config.training_data_uri,
        )

        sft_tuning_job.run(
            display_name=config.display_name,
            epochs=config.epochs,
            adapter_size=config.adapter_size,
            learning_rate_multiplier=config.learning_rate_multiplier,
        )

        logger.info("Launched SFT job: %s", sft_tuning_job.resource_name)

        return TuningJobResult(
            job_name=sft_tuning_job.resource_name,
            display_name=config.display_name,
            state=str(sft_tuning_job.state),
            create_time=str(sft_tuning_job.create_time),
            tuned_model_endpoint=str(
                getattr(sft_tuning_job, "tuned_model_endpoint_name", "")
            ),
            is_mock=False,
        )
