"""Tests for GCS upload functionality."""

import tempfile
from pathlib import Path

import pytest

from ai_writer.fine_tuning.jobs.gcs import GCSUploader


class TestGCSUploader:
    def test_mock_upload(self):
        uploader = GCSUploader(mock_mode=True)
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            f.write(b"test data\n")
            temp_path = Path(f.name)

        uri = uploader.upload(temp_path)
        assert uri.startswith("gs://")
        assert temp_path.name in uri
        temp_path.unlink()

    def test_mock_upload_with_prefix(self):
        uploader = GCSUploader(mock_mode=True)
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            f.write(b"test data\n")
            temp_path = Path(f.name)

        uri = uploader.upload(temp_path, gcs_prefix="my-data")
        assert "my-data" in uri
        temp_path.unlink()

    def test_file_not_found(self):
        uploader = GCSUploader(mock_mode=True)
        with pytest.raises(FileNotFoundError):
            uploader.upload("/nonexistent/file.jsonl")

    def test_mock_list_files(self):
        uploader = GCSUploader(mock_mode=True)
        files = uploader.list_files()
        assert len(files) >= 1
        assert all(f.startswith("gs://") for f in files)

    def test_mock_list_files_with_prefix(self):
        uploader = GCSUploader(mock_mode=True)
        files = uploader.list_files(prefix="custom-prefix")
        assert len(files) >= 1
        assert all("custom-prefix" in f for f in files)
