"""Run A/B comparison testbed between base and tuned models.

Usage:
    poetry run python scripts/ft_run_comparison.py --all
    poetry run python scripts/ft_run_comparison.py --categories scene_writing opening
    poetry run python scripts/ft_run_comparison.py --all --no-judge
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_writer.fine_tuning.comparison.report import ReportGenerator
from ai_writer.fine_tuning.comparison.runner import ComparisonRunner
from ai_writer.fine_tuning.config import ComparisonConfig


def main():
    parser = argparse.ArgumentParser(description="Run A/B comparison")
    parser.add_argument("--all", action="store_true", help="Run all prompt categories")
    parser.add_argument("--categories", nargs="+", help="Specific categories to run")
    parser.add_argument("--no-judge", action="store_true", help="Skip LLM-as-judge")
    parser.add_argument(
        "--output-dir", default="output/comparisons", help="Output directory"
    )
    parser.add_argument("--tuned-endpoint", default="", help="Tuned model endpoint")
    args = parser.parse_args()

    if not args.all and not args.categories:
        parser.error("Specify --all or --categories")

    categories = ["all"] if args.all else args.categories

    config = ComparisonConfig(
        categories=categories,
        output_dir=args.output_dir,
        tuned_model_endpoint=args.tuned_endpoint,
    )

    runner = ComparisonRunner(config=config)
    report = runner.run(with_judge=not args.no_judge)

    generator = ReportGenerator(output_dir=args.output_dir)
    paths = generator.generate(report)

    print("\nComparison complete!")
    print(f"  Prompts:    {report.prompt_count}")
    print(f"  Base wins:  {report.base_wins}")
    print(f"  Tuned wins: {report.tuned_wins}")
    print(f"  Ties:       {report.ties}")
    print(f"  Mock mode:  {report.is_mock}")
    print("\nReports:")
    print(f"  Text: {paths['text']}")
    print(f"  JSON: {paths['json']}")


if __name__ == "__main__":
    main()
