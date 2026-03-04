"""Google Cloud Storage upload for training data.

Handles uploading JSONL training files to GCS. In mock mode,
simulates the upload and returns a synthetic GCS URI.
"""

import logging
from pathlib import Path

from ai_writer.config import get_settings

logger = logging.getLogger("ai_writer.fine_tuning.jobs.gcs")


class GCSUploader:
    """Upload training data to Google Cloud Storage."""

    def __init__(self, mock_mode: bool | None = None):
        settings = get_settings()
        self.mock_mode = (
            mock_mode if mock_mode is not None else settings.fine_tuning_mock_mode
        )
        self.bucket_name = settings.vertex_bucket_name
        self.project_id = settings.vertex_project_id

    def upload(
        self,
        local_path: str | Path,
        gcs_prefix: str = "training-data",
    ) -> str:
        """Upload a file to GCS and return its URI.

        Args:
            local_path: Path to the local file.
            gcs_prefix: GCS prefix/folder for the upload.

        Returns:
            GCS URI (gs://bucket/prefix/filename).
        """
        path = Path(local_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        bucket = self.bucket_name or "mock-bucket"
        gcs_uri = f"gs://{bucket}/{gcs_prefix}/{path.name}"

        if self.mock_mode:
            logger.info("[MOCK] Would upload %s → %s", path, gcs_uri)
            return gcs_uri

        if not self.bucket_name:
            raise ValueError("vertex_bucket_name must be set when mock_mode=False")

        try:
            from google.cloud import storage
        except ImportError as exc:
            raise ImportError(
                "google-cloud-storage is required for real GCS uploads. "
                "Install with: poetry install --with fine-tuning"
            ) from exc

        client = storage.Client(project=self.project_id)
        bucket = client.bucket(self.bucket_name)
        blob_name = f"{gcs_prefix}/{path.name}"
        blob = bucket.blob(blob_name)

        logger.info("Uploading %s → %s", path, gcs_uri)
        blob.upload_from_filename(str(path))
        logger.info("Upload complete: %s", gcs_uri)

        return gcs_uri

    def list_files(self, prefix: str = "training-data") -> list[str]:
        """List files in the GCS bucket under a prefix.

        Returns:
            List of GCS URIs.
        """
        if self.mock_mode:
            logger.info(
                "[MOCK] Would list files under gs://%s/%s", self.bucket_name, prefix
            )
            return [
                f"gs://{self.bucket_name}/{prefix}/scene_writing.jsonl",
                f"gs://{self.bucket_name}/{prefix}/style_editing.jsonl",
            ]

        try:
            from google.cloud import storage
        except ImportError as exc:
            raise ImportError(
                "google-cloud-storage is required. "
                "Install with: poetry install --with fine-tuning"
            ) from exc

        client = storage.Client(project=self.project_id)
        bucket = client.bucket(self.bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        return [f"gs://{self.bucket_name}/{blob.name}" for blob in blobs]
