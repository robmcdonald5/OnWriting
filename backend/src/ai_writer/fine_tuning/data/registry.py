"""Training data auto-discovery, validation, and compilation.

Discovers JSONL files from training/ and validation/ directories,
validates them, and compiles into merged output for fine-tuning jobs.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ai_writer.fine_tuning.data.validator import ValidationReport, validate_jsonl

logger = logging.getLogger("ai_writer.fine_tuning.data.registry")

TRAINING_DIR = Path(__file__).parent / "training"
VALIDATION_DIR = Path(__file__).parent / "validation"
COMPILED_DIR = Path(__file__).parent / "compiled"


@dataclass
class FileMetadata:
    """Metadata parsed from a sidecar .md file's YAML frontmatter."""

    teaches: list[str] = field(default_factory=list)
    source: str = ""
    example_count: int | None = None
    notes: str = ""


@dataclass
class CompilationReport:
    """Result of discovering, validating, and compiling training data."""

    files_discovered: list[Path] = field(default_factory=list)
    per_file_reports: dict[str, ValidationReport] = field(default_factory=dict)
    per_file_metadata: dict[str, FileMetadata | None] = field(default_factory=dict)
    total_examples: int = 0
    total_user_tokens_approx: int = 0
    total_model_tokens_approx: int = 0
    output_path: Path | None = None
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        lines = [
            f"[{status}] Compilation Report",
            f"  Files discovered: {len(self.files_discovered)}",
        ]

        for f in self.files_discovered:
            key = str(f)
            report = self.per_file_reports.get(key)
            meta = self.per_file_metadata.get(key)
            mark = "OK" if report and report.is_valid else "FAIL"
            count = report.valid_lines if report else 0
            lines.append(f"    [{mark}] {f.name} ({count} examples)")
            if meta:
                lines.append(f"           teaches: {', '.join(meta.teaches)}")
                if meta.source:
                    lines.append(f"           source: {meta.source}")

        lines.append(f"  Total examples: {self.total_examples}")
        lines.append(
            f"  Approx tokens — user: {self.total_user_tokens_approx}, "
            f"model: {self.total_model_tokens_approx}"
        )

        if self.output_path:
            lines.append(f"  Output: {self.output_path}")

        if self.errors:
            lines.append(f"  Errors ({len(self.errors)}):")
            for err in self.errors:
                lines.append(f"    {err}")

        return "\n".join(lines)


def discover_training_files(
    categories: list[str] | None = None,
) -> list[Path]:
    """Discover JSONL files in the training directory.

    Args:
        categories: Optional filter — only include files whose stem matches.
                    e.g., ["scene_writing"] matches scene_writing.jsonl.

    Returns:
        Sorted list of discovered JSONL file paths.
    """
    return _discover_files(TRAINING_DIR, categories)


def discover_validation_files(
    categories: list[str] | None = None,
) -> list[Path]:
    """Discover JSONL files in the validation directory.

    Args:
        categories: Optional filter — only include files whose stem matches.

    Returns:
        Sorted list of discovered JSONL file paths.
    """
    return _discover_files(VALIDATION_DIR, categories)


def _discover_files(directory: Path, categories: list[str] | None = None) -> list[Path]:
    """Glob for JSONL files in a directory, optionally filtering by category."""
    if not directory.exists():
        return []

    files = sorted(directory.glob("*.jsonl"))

    if categories:
        files = [f for f in files if f.stem in categories]

    return files


def get_file_metadata(jsonl_path: Path) -> FileMetadata | None:
    """Parse companion .md sidecar frontmatter for a JSONL file.

    Looks for a .md file with the same stem as the JSONL file.
    Returns None if no sidecar exists.
    """
    md_path = jsonl_path.with_suffix(".md")
    if not md_path.exists():
        return None

    text = md_path.read_text(encoding="utf-8")
    return _parse_frontmatter(text)


def _parse_frontmatter(text: str) -> FileMetadata:
    """Parse YAML frontmatter from markdown text."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", text, re.DOTALL)
    if not match:
        return FileMetadata(notes=text.strip())

    frontmatter_text = match.group(1)
    body = match.group(2).strip()

    data = yaml.safe_load(frontmatter_text) or {}

    teaches = data.get("teaches", [])
    if isinstance(teaches, str):
        teaches = [teaches]

    example_count = data.get("example_count")
    if example_count is not None:
        try:
            example_count = int(example_count)
        except (ValueError, TypeError):
            example_count = None

    return FileMetadata(
        teaches=teaches,
        source=str(data.get("source", "")),
        example_count=example_count,
        notes=body,
    )


def compile_training_set(
    output_path: Path | None = None,
    categories: list[str] | None = None,
) -> CompilationReport:
    """Discover, validate, and compile training data into a single JSONL file.

    Args:
        output_path: Where to write the compiled output.
                     Defaults to compiled/training.jsonl.
        categories: Optional category filter for file discovery.

    Returns:
        CompilationReport with per-file details and aggregate stats.
    """
    if output_path is None:
        output_path = COMPILED_DIR / "training.jsonl"

    files = discover_training_files(categories)
    return _compile(files, output_path)


def compile_validation_set(
    output_path: Path | None = None,
    categories: list[str] | None = None,
) -> CompilationReport:
    """Discover, validate, and compile validation data into a single JSONL file.

    Args:
        output_path: Where to write the compiled output.
                     Defaults to compiled/validation.jsonl.
        categories: Optional category filter for file discovery.

    Returns:
        CompilationReport with per-file details and aggregate stats.
    """
    if output_path is None:
        output_path = COMPILED_DIR / "validation.jsonl"

    files = discover_validation_files(categories)
    return _compile(files, output_path)


def _compile(files: list[Path], output_path: Path) -> CompilationReport:
    """Validate files and merge valid ones into a single JSONL output."""
    report = CompilationReport(
        files_discovered=files,
        output_path=output_path,
    )

    if not files:
        report.errors.append("No JSONL files discovered")
        report.is_valid = False
        return report

    # Validate each file
    file_reports = _validate_all(files)
    report.per_file_reports = {str(f): r for f, r in file_reports.items()}

    # Collect metadata
    for f in files:
        meta = get_file_metadata(f)
        report.per_file_metadata[str(f)] = meta

    # Check for validation failures
    valid_files = []
    for f in files:
        r = file_reports[f]
        if r.is_valid:
            valid_files.append(f)
        else:
            report.errors.append(f"{f.name}: {len(r.errors)} validation errors")

    if not valid_files:
        report.is_valid = False
        report.errors.append("No valid files to compile")
        return report

    if len(valid_files) < len(files):
        report.is_valid = False

    # Merge valid files
    count = _merge_jsonl_files(valid_files, output_path)
    report.total_examples = count

    # Aggregate token counts from valid file reports
    for f in valid_files:
        r = file_reports[f]
        report.total_user_tokens_approx += r.total_user_tokens_approx
        report.total_model_tokens_approx += r.total_model_tokens_approx

    logger.info(
        "Compiled %d examples from %d files to %s",
        count,
        len(valid_files),
        output_path,
    )
    return report


def _validate_all(files: list[Path]) -> dict[Path, ValidationReport]:
    """Validate each JSONL file, reusing the existing validator."""
    results = {}
    for f in files:
        results[f] = validate_jsonl(f)
    return results


def _merge_jsonl_files(files: list[Path], output: Path) -> int:
    """Concatenate lines from multiple JSONL files into one output file.

    Returns:
        Total number of lines written.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0

    with open(output, "w", encoding="utf-8") as out_f:
        for f in files:
            with open(f, encoding="utf-8") as in_f:
                for line in in_f:
                    stripped = line.strip()
                    if stripped:
                        out_f.write(stripped + "\n")
                        count += 1

    return count
