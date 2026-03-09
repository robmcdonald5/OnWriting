"""Launch a Vertex AI supervised fine-tuning job.

Usage:
    poetry run python scripts/ft_launch_job.py                                # auto-discover and compile
    poetry run python scripts/ft_launch_job.py --data gs://bucket/path.jsonl  # explicit data path
    poetry run python scripts/ft_launch_job.py --categories scene_writing     # filter categories
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_writer.fine_tuning.config import FineTuningJobConfig
from ai_writer.fine_tuning.data.registry import (
    compile_training_set,
    compile_validation_set,
    discover_validation_files,
)
from ai_writer.fine_tuning.jobs.gcs import GCSUploader
from ai_writer.fine_tuning.jobs.launcher import FineTuningLauncher


def main():
    parser = argparse.ArgumentParser(description="Launch SFT job")
    parser.add_argument(
        "--data",
        default=None,
        help="Training data path (local or GCS URI). "
        "If omitted, auto-discovers and compiles from training/",
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
        "--categories",
        nargs="+",
        default=None,
        help="Only include these training data categories",
    )
    parser.add_argument(
        "--no-validation-set",
        action="store_true",
        help="Skip validation data even if validation/ has files",
    )
    args = parser.parse_args()

    data_uri = args.data
    validation_uri = ""

    if data_uri is None:
        # Auto-discover and compile
        print("Auto-discovering training data...")
        train_report = compile_training_set(categories=args.categories)
        print(train_report.summary())
        print()

        if not train_report.is_valid:
            print("ERROR: Training data has validation errors. Aborting.")
            sys.exit(1)

        data_uri = str(train_report.output_path)

        # Auto-discover validation data
        if not args.no_validation_set:
            val_files = discover_validation_files(args.categories)
            if val_files:
                print("Auto-discovering validation data...")
                val_report = compile_validation_set(categories=args.categories)
                print(val_report.summary())
                print()

                if val_report.is_valid and val_report.output_path:
                    validation_uri = str(val_report.output_path)

    if args.upload and not data_uri.startswith("gs://"):
        uploader = GCSUploader()
        data_uri = uploader.upload(data_uri)
        print(f"Uploaded training data to: {data_uri}")

        if validation_uri and not validation_uri.startswith("gs://"):
            validation_uri = uploader.upload(validation_uri)
            print(f"Uploaded validation data to: {validation_uri}")

    config = FineTuningJobConfig(
        source_model=args.model,
        training_data_uri=data_uri,
        validation_data_uri=validation_uri,
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
