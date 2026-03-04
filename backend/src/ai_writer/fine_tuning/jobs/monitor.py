"""Vertex AI tuning job monitor.

Check job status, list tuned models, and retrieve job metadata.
In mock mode, returns synthetic status information.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from ai_writer.config import get_settings

logger = logging.getLogger("ai_writer.fine_tuning.jobs.monitor")


@dataclass
class JobStatus:
    """Status of a tuning job."""

    job_name: str
    state: str
    create_time: str
    update_time: str
    error_message: str = ""
    tuned_model_endpoint: str = ""
    is_mock: bool = False


@dataclass
class TunedModelInfo:
    """Information about a tuned model."""

    model_name: str
    endpoint: str
    source_model: str
    create_time: str
    is_mock: bool = False


class JobMonitor:
    """Monitor Vertex AI tuning jobs and list tuned models."""

    def __init__(self, mock_mode: bool | None = None):
        settings = get_settings()
        self.mock_mode = (
            mock_mode if mock_mode is not None else settings.fine_tuning_mock_mode
        )
        self.project_id = settings.vertex_project_id
        self.region = settings.vertex_region

    def check_status(self, job_name: str) -> JobStatus:
        """Check the status of a tuning job.

        Args:
            job_name: Full resource name of the tuning job.

        Returns:
            JobStatus with current state.
        """
        if self.mock_mode:
            return self._mock_status(job_name)

        return self._real_status(job_name)

    def list_tuned_models(self) -> list[TunedModelInfo]:
        """List all available tuned models.

        Returns:
            List of TunedModelInfo objects.
        """
        if self.mock_mode:
            return self._mock_list_models()

        return self._real_list_models()

    def _mock_status(self, job_name: str) -> JobStatus:
        """Return synthetic job status."""
        now = datetime.now(timezone.utc).isoformat()
        logger.info("[MOCK] Checking status for: %s", job_name)

        return JobStatus(
            job_name=job_name,
            state="JOB_STATE_SUCCEEDED",
            create_time=now,
            update_time=now,
            tuned_model_endpoint="projects/mock-project/locations/us-central1/endpoints/mock-endpoint-123",
            is_mock=True,
        )

    def _mock_list_models(self) -> list[TunedModelInfo]:
        """Return synthetic tuned model list."""
        logger.info("[MOCK] Listing tuned models")
        now = datetime.now(timezone.utc).isoformat()
        return [
            TunedModelInfo(
                model_name="ai-writer-sft-v1",
                endpoint="projects/mock-project/locations/us-central1/endpoints/mock-endpoint-123",
                source_model="gemini-2.5-flash",
                create_time=now,
                is_mock=True,
            ),
            TunedModelInfo(
                model_name="ai-writer-sft-v2",
                endpoint="projects/mock-project/locations/us-central1/endpoints/mock-endpoint-456",
                source_model="gemini-2.5-flash",
                create_time=now,
                is_mock=True,
            ),
        ]

    def _real_status(self, job_name: str) -> JobStatus:
        """Check real job status via Vertex AI API."""
        try:
            from google.cloud import aiplatform
        except ImportError as exc:
            raise ImportError(
                "google-cloud-aiplatform is required. "
                "Install with: poetry install --with fine-tuning"
            ) from exc

        aiplatform.init(project=self.project_id, location=self.region)
        job = aiplatform.SupervisedTuningJob(job_name)

        return JobStatus(
            job_name=job.resource_name,
            state=str(job.state),
            create_time=str(job.create_time),
            update_time=str(job.update_time),
            error_message=str(getattr(job, "error", "")),
            tuned_model_endpoint=str(getattr(job, "tuned_model_endpoint_name", "")),
            is_mock=False,
        )

    def _real_list_models(self) -> list[TunedModelInfo]:
        """List real tuned models via Vertex AI API."""
        try:
            from google.cloud import aiplatform
        except ImportError as exc:
            raise ImportError(
                "google-cloud-aiplatform is required. "
                "Install with: poetry install --with fine-tuning"
            ) from exc

        aiplatform.init(project=self.project_id, location=self.region)
        jobs = aiplatform.SupervisedTuningJob.list()

        models = []
        for job in jobs:
            endpoint = str(getattr(job, "tuned_model_endpoint_name", ""))
            if endpoint:
                models.append(
                    TunedModelInfo(
                        model_name=job.display_name,
                        endpoint=endpoint,
                        source_model=str(getattr(job, "source_model", "unknown")),
                        create_time=str(job.create_time),
                        is_mock=False,
                    )
                )

        return models
