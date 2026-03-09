"""Tests for pipeline output to training data conversion."""

import tempfile
from pathlib import Path

from ai_writer.fine_tuning.data.converter import (
    convert_pipeline_output,
    convert_scene_to_example,
    write_examples_to_jsonl,
)
from ai_writer.fine_tuning.data.validator import validate_jsonl


class TestConvertSceneToExample:
    def test_basic_conversion(self):
        example = convert_scene_to_example(
            scene_outline="A man walks into a bar.",
            approved_prose="Marcus pushed open the door.",
        )
        assert example.contents[0].role == "user"
        assert example.contents[1].role == "model"
        assert "Marcus" in example.contents[1].parts[0].text
        assert example.systemInstruction is not None

    def test_with_context(self):
        example = convert_scene_to_example(
            scene_outline="Scene outline",
            approved_prose="Prose output",
            context="Character: Marcus, Age: 30",
        )
        user_text = example.contents[0].parts[0].text
        assert "Marcus" in user_text
        assert "Scene outline" in user_text

    def test_custom_system_instruction(self):
        example = convert_scene_to_example(
            scene_outline="outline",
            approved_prose="prose",
            system_instruction="Custom system prompt",
        )
        assert example.systemInstruction is not None
        assert example.systemInstruction.parts[0].text == "Custom system prompt"


class TestConvertPipelineOutput:
    def test_empty_state(self):
        examples = convert_pipeline_output({})
        assert examples == []

    def test_with_scene_drafts(self):
        state = {
            "scene_drafts": [
                {"prose": "The rain fell on the empty street."},
                {"prose": "She opened the letter with trembling hands."},
            ],
        }
        examples = convert_pipeline_output(state)
        assert len(examples) == 2

    def test_skips_empty_prose(self):
        state = {
            "scene_drafts": [
                {"prose": "Valid prose here."},
                {"prose": ""},
                {"prose": None},
            ],
        }
        examples = convert_pipeline_output(state)
        assert len(examples) == 1


class TestWriteExamplesToJsonl:
    def test_write_and_validate(self):
        examples = [
            convert_scene_to_example(
                scene_outline=f"Scene {i}",
                approved_prose=f"Prose for scene {i} with enough text to be valid.",
            )
            for i in range(3)
        ]

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_path = Path(f.name)

        write_examples_to_jsonl(examples, output_path)

        assert output_path.exists()
        with open(output_path) as f:
            lines = f.readlines()
        assert len(lines) == 3

        # Validate the output
        report = validate_jsonl(output_path)
        assert report.is_valid

        output_path.unlink()
