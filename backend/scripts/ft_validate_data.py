"""Validate JSONL training data files against Vertex AI format.

Usage:
    poetry run python scripts/ft_validate_data.py <path-to-jsonl>
    poetry run python scripts/ft_validate_data.py --all
"""

import argparse
import sys
from pathlib import Path

# Ensure backend/src is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_writer.fine_tuning.data.registry import (
    discover_training_files,
    discover_validation_files,
)
from ai_writer.fine_tuning.data.validator import validate_jsonl


def main():
    parser = argparse.ArgumentParser(description="Validate training data")
    parser.add_argument("file", nargs="?", help="Path to JSONL file to validate")
    parser.add_argument(
        "--all",
        action="store_true",
        dest="validate_all",
        help="Discover and validate all files in training/ and validation/",
    )
    args = parser.parse_args()

    if not args.file and not args.validate_all:
        parser.print_help()
        sys.exit(1)

    if args.validate_all:
        all_valid = True
        training = discover_training_files()
        validation = discover_validation_files()

        if training:
            print("=== Training Files ===\n")
            for f in training:
                report = validate_jsonl(f)
                print(report.summary())
                print()
                if not report.is_valid:
                    all_valid = False

        if validation:
            print("=== Validation Files ===\n")
            for f in validation:
                report = validate_jsonl(f)
                print(report.summary())
                print()
                if not report.is_valid:
                    all_valid = False

        if not training and not validation:
            print("No JSONL files found in training/ or validation/")
            sys.exit(1)

        sys.exit(0 if all_valid else 1)

    # Single file mode
    report = validate_jsonl(args.file)
    print(report.summary())
    sys.exit(0 if report.is_valid else 1)


if __name__ == "__main__":
    main()
