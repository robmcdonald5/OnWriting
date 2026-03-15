"""Convert pipeline outputs to training data JSONL.

Usage:
    poetry run python scripts/ft_convert_outputs.py --input output/pipeline_state.json --output training_data.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_writer.fine_tuning.data.converter import (
    convert_pipeline_output,
    write_examples_to_jsonl,
)
from ai_writer.fine_tuning.data.validator import validate_jsonl


def main():
    parser = argparse.ArgumentParser(
        description="Convert pipeline outputs to training JSONL"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to pipeline state JSON file",
    )
    parser.add_argument(
        "--output",
        default="training_data.jsonl",
        help="Output JSONL file path",
    )
    parser.add_argument(
        "--validate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Validate output after conversion (default: true)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    with open(input_path) as f:
        state = json.load(f)

    examples = convert_pipeline_output(state)

    if not examples:
        print(
            "No training examples generated. Check that the pipeline state contains approved scenes."
        )
        sys.exit(1)

    output_path = write_examples_to_jsonl(examples, args.output)
    print(f"Wrote {len(examples)} examples to {output_path}")

    if args.validate:
        report = validate_jsonl(output_path)
        print(f"\nValidation: {report.summary()}")


if __name__ == "__main__":
    main()
