"""Validate JSONL training data files against Vertex AI format.

Usage:
    poetry run python scripts/ft_validate_data.py <path-to-jsonl>
    poetry run python scripts/ft_validate_data.py src/ai_writer/fine_tuning/data/templates/scene_writing.jsonl
"""

import sys
from pathlib import Path

# Ensure backend/src is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_writer.fine_tuning.data.validator import validate_jsonl


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ft_validate_data.py <path-to-jsonl>")
        sys.exit(1)

    file_path = sys.argv[1]
    report = validate_jsonl(file_path)
    print(report.summary())
    sys.exit(0 if report.is_valid else 1)


if __name__ == "__main__":
    main()
