"""Tests for JSONL validation."""

import json
import tempfile
from pathlib import Path

from ai_writer.fine_tuning.data.validator import validate_jsonl


def _write_jsonl(lines: list[str], suffix: str = ".jsonl") -> Path:
    """Write lines to a temp JSONL file and return its path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    )
    for line in lines:
        f.write(line + "\n")
    f.close()
    return Path(f.name)


def _valid_example() -> str:
    """Return a valid training example as JSON string."""
    return json.dumps(
        {
            "systemInstruction": {
                "role": "system",
                "parts": [{"text": "You are a writer"}],
            },
            "contents": [
                {"role": "user", "parts": [{"text": "Write a scene"}]},
                {"role": "model", "parts": [{"text": "The door opened slowly."}]},
            ],
        }
    )


class TestValidateJsonl:
    def test_valid_file(self):
        path = _write_jsonl([_valid_example(), _valid_example()])
        report = validate_jsonl(path)
        assert report.is_valid
        assert report.total_lines == 2
        assert report.valid_lines == 2
        assert report.total_user_tokens_approx > 0
        assert report.total_model_tokens_approx > 0
        Path(path).unlink()

    def test_file_not_found(self):
        report = validate_jsonl("/nonexistent/file.jsonl")
        assert not report.is_valid
        assert "not found" in report.errors[0].message.lower()

    def test_invalid_json(self):
        path = _write_jsonl([_valid_example(), "not valid json {{{"])
        report = validate_jsonl(path)
        assert not report.is_valid
        assert report.valid_lines == 1
        assert len(report.errors) == 1
        assert report.errors[0].line_number == 2
        Path(path).unlink()

    def test_empty_line(self):
        path = _write_jsonl([_valid_example(), "", _valid_example()])
        report = validate_jsonl(path)
        assert not report.is_valid
        assert report.valid_lines == 2
        assert len(report.errors) == 1
        Path(path).unlink()

    def test_schema_violation(self):
        bad_example = json.dumps(
            {
                "contents": [
                    {"role": "user", "parts": [{"text": "hi"}]},
                    # Missing model turn at end
                    {"role": "user", "parts": [{"text": "again"}]},
                ]
            }
        )
        path = _write_jsonl([bad_example])
        report = validate_jsonl(path)
        assert not report.is_valid
        assert report.valid_lines == 0
        Path(path).unlink()

    def test_wrong_extension_warns(self):
        path = _write_jsonl([_valid_example()], suffix=".json")
        report = validate_jsonl(path)
        # Still validates content but reports extension issue
        assert len(report.errors) >= 1
        Path(path).unlink()

    def test_summary_format(self):
        path = _write_jsonl([_valid_example()])
        report = validate_jsonl(path)
        summary = report.summary()
        assert "VALID" in summary
        assert "1/1" in summary
        Path(path).unlink()

    def test_template_files_valid(self):
        """Validate the shipped template files."""
        templates_dir = (
            Path(__file__).parent.parent.parent
            / "src"
            / "ai_writer"
            / "fine_tuning"
            / "data"
            / "templates"
        )
        for jsonl_file in templates_dir.glob("*.jsonl"):
            report = validate_jsonl(jsonl_file)
            assert (
                report.is_valid
            ), f"Template {jsonl_file.name} is invalid:\n{report.summary()}"
