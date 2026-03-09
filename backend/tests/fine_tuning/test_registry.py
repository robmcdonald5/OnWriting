"""Tests for training data auto-discovery and compilation registry."""

import json
from pathlib import Path

from ai_writer.fine_tuning.data.registry import (
    CompilationReport,
    _parse_frontmatter,
    compile_training_set,
    compile_validation_set,
    discover_training_files,
    discover_validation_files,
    get_file_metadata,
)

# Minimal valid training example for test JSONL files
VALID_EXAMPLE = {
    "systemInstruction": {
        "role": "system",
        "parts": [{"text": "You are a writer."}],
    },
    "contents": [
        {"role": "user", "parts": [{"text": "Write a scene about rain."}]},
        {"role": "model", "parts": [{"text": "The rain fell on the empty street."}]},
    ],
}


def _write_jsonl(path: Path, examples: list[dict]) -> None:
    """Helper to write examples to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")


class TestDiscoverTrainingFiles:
    def test_discover_training_files(self):
        """Finds all JSONL files in the actual training/ directory."""
        files = discover_training_files()
        assert len(files) >= 2  # seed data: scene_writing + style_editing
        assert all(f.suffix == ".jsonl" for f in files)
        names = [f.stem for f in files]
        assert "scene_writing" in names
        assert "style_editing" in names

    def test_discover_empty_directory(self, tmp_path):
        """Returns empty list for directory with no JSONL files."""
        from ai_writer.fine_tuning.data import registry

        original = registry.TRAINING_DIR
        registry.TRAINING_DIR = tmp_path / "empty"
        registry.TRAINING_DIR.mkdir()

        try:
            files = discover_training_files()
            assert files == []
        finally:
            registry.TRAINING_DIR = original

    def test_discover_nonexistent_directory(self, tmp_path):
        """Returns empty list when directory doesn't exist."""
        from ai_writer.fine_tuning.data import registry

        original = registry.TRAINING_DIR
        registry.TRAINING_DIR = tmp_path / "nonexistent"

        try:
            files = discover_training_files()
            assert files == []
        finally:
            registry.TRAINING_DIR = original

    def test_discover_with_category_filter(self, tmp_path):
        """Only includes files matching requested categories."""
        from ai_writer.fine_tuning.data import registry

        original = registry.TRAINING_DIR
        registry.TRAINING_DIR = tmp_path

        _write_jsonl(tmp_path / "scene_writing.jsonl", [VALID_EXAMPLE])
        _write_jsonl(tmp_path / "style_editing.jsonl", [VALID_EXAMPLE])
        _write_jsonl(tmp_path / "dialogue.jsonl", [VALID_EXAMPLE])

        try:
            files = discover_training_files(categories=["scene_writing", "dialogue"])
            names = [f.stem for f in files]
            assert "scene_writing" in names
            assert "dialogue" in names
            assert "style_editing" not in names
        finally:
            registry.TRAINING_DIR = original


class TestDiscoverValidationFiles:
    def test_discover_validation_files(self):
        """Discovers files from validation/ directory."""
        files = discover_validation_files()
        # May be empty initially
        assert isinstance(files, list)


class TestCompileTrainingSet:
    def test_compile_training_set(self, tmp_path):
        """Merges files, validates, and returns a report."""
        from ai_writer.fine_tuning.data import registry

        original_train = registry.TRAINING_DIR
        original_compiled = registry.COMPILED_DIR
        registry.TRAINING_DIR = tmp_path / "training"
        registry.COMPILED_DIR = tmp_path / "compiled"

        _write_jsonl(
            registry.TRAINING_DIR / "cat_a.jsonl", [VALID_EXAMPLE, VALID_EXAMPLE]
        )
        _write_jsonl(registry.TRAINING_DIR / "cat_b.jsonl", [VALID_EXAMPLE])

        try:
            report = compile_training_set()
            assert report.is_valid
            assert report.total_examples == 3
            assert len(report.files_discovered) == 2
            assert report.output_path is not None
            assert report.output_path.exists()

            # Verify merged output has correct line count
            with open(report.output_path) as f:
                lines = [line for line in f.readlines() if line.strip()]
            assert len(lines) == 3
        finally:
            registry.TRAINING_DIR = original_train
            registry.COMPILED_DIR = original_compiled

    def test_compile_with_category_filter(self, tmp_path):
        """Only includes matching categories in compilation."""
        from ai_writer.fine_tuning.data import registry

        original_train = registry.TRAINING_DIR
        original_compiled = registry.COMPILED_DIR
        registry.TRAINING_DIR = tmp_path / "training"
        registry.COMPILED_DIR = tmp_path / "compiled"

        _write_jsonl(
            registry.TRAINING_DIR / "scene_writing.jsonl",
            [VALID_EXAMPLE, VALID_EXAMPLE],
        )
        _write_jsonl(registry.TRAINING_DIR / "style_editing.jsonl", [VALID_EXAMPLE])

        try:
            report = compile_training_set(categories=["scene_writing"])
            assert report.is_valid
            assert report.total_examples == 2
            assert len(report.files_discovered) == 1
        finally:
            registry.TRAINING_DIR = original_train
            registry.COMPILED_DIR = original_compiled

    def test_compile_with_invalid_file(self, tmp_path):
        """Reports errors and marks compilation as invalid."""
        from ai_writer.fine_tuning.data import registry

        original_train = registry.TRAINING_DIR
        original_compiled = registry.COMPILED_DIR
        registry.TRAINING_DIR = tmp_path / "training"
        registry.COMPILED_DIR = tmp_path / "compiled"

        _write_jsonl(registry.TRAINING_DIR / "good.jsonl", [VALID_EXAMPLE])
        # Write invalid JSONL
        bad_path = registry.TRAINING_DIR / "bad.jsonl"
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_text("not valid json\n", encoding="utf-8")

        try:
            report = compile_training_set()
            assert not report.is_valid
            assert len(report.errors) > 0
            # Good file still compiled
            assert report.total_examples == 1
        finally:
            registry.TRAINING_DIR = original_train
            registry.COMPILED_DIR = original_compiled

    def test_compile_empty_directory(self, tmp_path):
        """Returns invalid report for empty directory."""
        from ai_writer.fine_tuning.data import registry

        original_train = registry.TRAINING_DIR
        original_compiled = registry.COMPILED_DIR
        registry.TRAINING_DIR = tmp_path / "empty_training"
        registry.COMPILED_DIR = tmp_path / "compiled"
        registry.TRAINING_DIR.mkdir()

        try:
            report = compile_training_set()
            assert not report.is_valid
            assert "No JSONL files discovered" in report.errors
        finally:
            registry.TRAINING_DIR = original_train
            registry.COMPILED_DIR = original_compiled


class TestGetFileMetadata:
    def test_parse_sidecar_frontmatter(self, tmp_path):
        """Parses YAML frontmatter from companion .md file."""
        jsonl_path = tmp_path / "scene_writing.jsonl"
        _write_jsonl(jsonl_path, [VALID_EXAMPLE])

        md_path = tmp_path / "scene_writing.md"
        md_path.write_text(
            "---\n"
            "teaches:\n"
            "  - sensory_detail\n"
            "  - pacing\n"
            'source: "Hand-crafted examples"\n'
            "example_count: 3\n"
            "---\n"
            "\n"
            "Some notes about the data.\n",
            encoding="utf-8",
        )

        meta = get_file_metadata(jsonl_path)
        assert meta is not None
        assert meta.teaches == ["sensory_detail", "pacing"]
        assert meta.source == "Hand-crafted examples"
        assert meta.example_count == 3
        assert "notes about the data" in meta.notes

    def test_missing_sidecar_returns_none(self, tmp_path):
        """Returns None when no companion .md exists."""
        jsonl_path = tmp_path / "orphan.jsonl"
        _write_jsonl(jsonl_path, [VALID_EXAMPLE])

        meta = get_file_metadata(jsonl_path)
        assert meta is None

    def test_parse_frontmatter_no_frontmatter(self):
        """Handles .md files without YAML frontmatter."""
        meta = _parse_frontmatter("Just some notes without frontmatter.")
        assert meta.teaches == []
        assert meta.source == ""
        assert meta.notes == "Just some notes without frontmatter."


class TestCompilationReportSummary:
    def test_summary_output(self):
        """Summary produces human-readable output."""
        report = CompilationReport(
            files_discovered=[Path("a.jsonl"), Path("b.jsonl")],
            total_examples=5,
            total_user_tokens_approx=100,
            total_model_tokens_approx=200,
            output_path=Path("compiled/training.jsonl"),
            is_valid=True,
        )
        summary = report.summary()
        assert "[VALID]" in summary
        assert "5" in summary
        assert "compiled" in summary

    def test_summary_invalid(self):
        """Summary shows INVALID status and errors."""
        report = CompilationReport(
            is_valid=False,
            errors=["No JSONL files discovered"],
        )
        summary = report.summary()
        assert "[INVALID]" in summary
        assert "No JSONL files discovered" in summary


class TestCompileValidationSet:
    def test_compile_validation_set(self, tmp_path):
        """Compiles validation files into separate output."""
        from ai_writer.fine_tuning.data import registry

        original_val = registry.VALIDATION_DIR
        original_compiled = registry.COMPILED_DIR
        registry.VALIDATION_DIR = tmp_path / "validation"
        registry.COMPILED_DIR = tmp_path / "compiled"

        _write_jsonl(registry.VALIDATION_DIR / "scene_writing.jsonl", [VALID_EXAMPLE])

        try:
            report = compile_validation_set()
            assert report.is_valid
            assert report.total_examples == 1
            assert "validation" in str(report.output_path)
        finally:
            registry.VALIDATION_DIR = original_val
            registry.COMPILED_DIR = original_compiled
