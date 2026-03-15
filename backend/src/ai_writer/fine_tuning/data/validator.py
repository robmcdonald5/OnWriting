"""JSONL training data validation.

Validates training files against the Vertex AI JSONL format before upload.
Reports per-line errors and aggregate statistics.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from ai_writer.fine_tuning.data.schemas import TrainingExample

logger = logging.getLogger("ai_writer.fine_tuning.data.validator")


@dataclass
class LineValidationError:
    """A single validation error for a training example."""

    line_number: int
    message: str
    raw_line: str = ""


@dataclass
class ValidationReport:
    """Result of validating a JSONL training file."""

    file_path: str
    total_lines: int = 0
    valid_lines: int = 0
    errors: list[LineValidationError] = field(default_factory=list)
    total_user_tokens_approx: int = 0
    total_model_tokens_approx: int = 0

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0 and self.total_lines > 0

    @property
    def error_rate(self) -> float:
        if self.total_lines == 0:
            return 0.0
        return len(self.errors) / self.total_lines

    def summary(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        lines = [
            f"[{status}] {self.file_path}",
            f"  Lines: {self.valid_lines}/{self.total_lines} valid",
            f"  Approx tokens — user: {self.total_user_tokens_approx}, "
            f"model: {self.total_model_tokens_approx}",
        ]
        if self.errors:
            lines.append(f"  Errors ({len(self.errors)}):")
            for err in self.errors[:10]:
                lines.append(f"    Line {err.line_number}: {err.message}")
            if len(self.errors) > 10:
                lines.append(f"    ... and {len(self.errors) - 10} more")
        return "\n".join(lines)


def _approx_token_count(text: str) -> int:
    """Rough token estimate (~4 chars per token)."""
    return max(1, len(text) // 4)


def validate_jsonl(file_path: str | Path) -> ValidationReport:
    """Validate a JSONL training file against Vertex AI format.

    Returns a ValidationReport with per-line errors and aggregate stats.
    """
    path = Path(file_path)
    report = ValidationReport(file_path=str(path))

    if not path.exists():
        report.errors.append(
            LineValidationError(
                line_number=0,
                message=f"File not found: {path}",
            )
        )
        return report

    if not path.suffix == ".jsonl":
        report.errors.append(
            LineValidationError(
                line_number=0,
                message=f"Expected .jsonl extension, got '{path.suffix}'",
            )
        )

    with open(path, encoding="utf-8") as f:
        for line_num, raw_line in enumerate(f, start=1):
            report.total_lines += 1
            stripped = raw_line.strip()

            if not stripped:
                report.errors.append(
                    LineValidationError(
                        line_number=line_num,
                        message="Empty line",
                        raw_line=stripped,
                    )
                )
                continue

            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as e:
                report.errors.append(
                    LineValidationError(
                        line_number=line_num,
                        message=f"Invalid JSON: {e}",
                        raw_line=stripped[:200],
                    )
                )
                continue

            try:
                example = TrainingExample.model_validate(data)
            except ValidationError as e:
                report.errors.append(
                    LineValidationError(
                        line_number=line_num,
                        message=str(e),
                        raw_line=stripped[:200],
                    )
                )
                continue

            report.valid_lines += 1

            for turn in example.contents:
                text = " ".join(p.text for p in turn.parts)
                tokens = _approx_token_count(text)
                if turn.role == "user":
                    report.total_user_tokens_approx += tokens
                else:
                    report.total_model_tokens_approx += tokens

    logger.info(
        "Validated %s: %d/%d valid",
        path.name,
        report.valid_lines,
        report.total_lines,
    )
    return report
