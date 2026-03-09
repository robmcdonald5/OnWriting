"""Compile training data from auto-discovered JSONL files.

Usage:
    poetry run python scripts/ft_compile_data.py                              # compile all
    poetry run python scripts/ft_compile_data.py --categories scene_writing   # filter
    poetry run python scripts/ft_compile_data.py --validate-only              # validate without merging
    poetry run python scripts/ft_compile_data.py --dry-run                    # show what would be discovered
    poetry run python scripts/ft_compile_data.py --info                       # show file metadata
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_writer.fine_tuning.data.registry import (
    compile_training_set,
    compile_validation_set,
    discover_training_files,
    discover_validation_files,
    get_file_metadata,
)
from ai_writer.fine_tuning.data.validator import validate_jsonl


def main():
    parser = argparse.ArgumentParser(description="Compile training data")
    parser.add_argument(
        "--categories",
        nargs="+",
        default=None,
        help="Only include files matching these categories",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate all files without merging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be discovered without processing",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show file metadata from sidecar .md files",
    )
    args = parser.parse_args()

    training_files = discover_training_files(args.categories)
    validation_files = discover_validation_files(args.categories)

    if args.dry_run:
        print("Training files:")
        for f in training_files:
            print(f"  {f.name}")
        print("\nValidation files:")
        for f in validation_files:
            print(f"  {f.name}")
        print(
            f"\nTotal: {len(training_files)} training, "
            f"{len(validation_files)} validation"
        )
        sys.exit(0)

    if args.info:
        print("Training file metadata:")
        for f in training_files:
            meta = get_file_metadata(f)
            print(f"\n  {f.name}:")
            if meta:
                print(f"    teaches: {', '.join(meta.teaches)}")
                print(f"    source: {meta.source}")
                print(f"    example_count: {meta.example_count}")
                if meta.notes:
                    print(f"    notes: {meta.notes[:100]}")
            else:
                print("    (no sidecar metadata)")
        sys.exit(0)

    if args.validate_only:
        all_valid = True
        all_files = training_files + validation_files
        for f in all_files:
            report = validate_jsonl(f)
            print(report.summary())
            print()
            if not report.is_valid:
                all_valid = False
        sys.exit(0 if all_valid else 1)

    # Full compilation
    print("Compiling training set...")
    train_report = compile_training_set(categories=args.categories)
    print(train_report.summary())
    print()

    if validation_files:
        print("Compiling validation set...")
        val_report = compile_validation_set(categories=args.categories)
        print(val_report.summary())
        print()

    sys.exit(0 if train_report.is_valid else 1)


if __name__ == "__main__":
    main()
