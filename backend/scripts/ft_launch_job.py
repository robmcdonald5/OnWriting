"""Launch a Vertex AI supervised fine-tuning job.

Usage:
    poetry run python scripts/ft_launch_job.py --data gs://bucket/path.jsonl
    poetry run python scripts/ft_launch_job.py --data path/to/local.jsonl --upload
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_writer.fine_tuning.config import FineTuningJobConfig
from ai_writer.fine_tuning.jobs.gcs import GCSUploader
from ai_writer.fine_tuning.jobs.launcher import FineTuningLauncher


def main():
    parser = argparse.ArgumentParser(description="Launch SFT job")
    parser.add_argument(
        "--data", required=True, help="Training data path (local or GCS URI)"
    )
    parser.add_argument(
        "--upload", action="store_true", help="Upload local file to GCS first"
    )
    parser.add_argument("--name", default="ai-writer-sft", help="Job display name")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Source model")
    parser.add_argument("--epochs", type=int, default=4, help="Training epochs")
    parser.add_argument("--adapter-size", type=int, default=4, help="LoRA adapter size")
    parser.add_argument(
        "--lr-multiplier", type=float, default=1.0, help="Learning rate multiplier"
    )
    parser.add_argument(
        "--validation-data", default="", help="GCS URI of validation JSONL"
    )
    args = parser.parse_args()

    data_uri = args.data

    if args.upload and not data_uri.startswith("gs://"):
        uploader = GCSUploader()
        data_uri = uploader.upload(data_uri)
        print(f"Uploaded to: {data_uri}")

    config = FineTuningJobConfig(
        source_model=args.model,
        training_data_uri=data_uri,
        validation_data_uri=args.validation_data,
        display_name=args.name,
        epochs=args.epochs,
        adapter_size=args.adapter_size,
        learning_rate_multiplier=args.lr_multiplier,
    )

    launcher = FineTuningLauncher()
    result = launcher.launch(config)

    print("\nJob launched:")
    print(f"  Name:     {result.job_name}")
    print(f"  State:    {result.state}")
    print(f"  Mock:     {result.is_mock}")
    if result.tuned_model_endpoint:
        print(f"  Endpoint: {result.tuned_model_endpoint}")


if __name__ == "__main__":
    main()
