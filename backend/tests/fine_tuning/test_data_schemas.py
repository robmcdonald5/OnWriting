"""Tests for training data schemas."""

import pytest
from pydantic import ValidationError

from ai_writer.fine_tuning.data.schemas import (
    ContentPart,
    ConversationTurn,
    SystemInstruction,
    TrainingExample,
)


class TestContentPart:
    def test_valid(self):
        p = ContentPart(text="hello")
        assert p.text == "hello"

    def test_empty_text_rejected(self):
        with pytest.raises(ValidationError):
            ContentPart(text="")


class TestConversationTurn:
    def test_valid_user(self):
        t = ConversationTurn(role="user", parts=[ContentPart(text="hi")])
        assert t.role == "user"

    def test_valid_model(self):
        t = ConversationTurn(role="model", parts=[ContentPart(text="hello")])
        assert t.role == "model"

    def test_invalid_role_rejected(self):
        with pytest.raises(ValidationError):
            ConversationTurn(role="assistant", parts=[ContentPart(text="hi")])

    def test_empty_parts_rejected(self):
        with pytest.raises(ValidationError):
            ConversationTurn(role="user", parts=[])


class TestTrainingExample:
    def test_valid_minimal(self):
        ex = TrainingExample(
            contents=[
                ConversationTurn(role="user", parts=[ContentPart(text="prompt")]),
                ConversationTurn(role="model", parts=[ContentPart(text="response")]),
            ]
        )
        assert len(ex.contents) == 2
        assert ex.systemInstruction is None

    def test_valid_with_system(self):
        ex = TrainingExample(
            systemInstruction=SystemInstruction(
                parts=[ContentPart(text="You are a writer")]
            ),
            contents=[
                ConversationTurn(role="user", parts=[ContentPart(text="prompt")]),
                ConversationTurn(role="model", parts=[ContentPart(text="response")]),
            ],
        )
        assert ex.systemInstruction is not None

    def test_last_turn_must_be_model(self):
        with pytest.raises(ValidationError, match="Last turn must be from 'model'"):
            TrainingExample(
                contents=[
                    ConversationTurn(role="user", parts=[ContentPart(text="a")]),
                    ConversationTurn(role="model", parts=[ContentPart(text="b")]),
                    ConversationTurn(role="user", parts=[ContentPart(text="c")]),
                ]
            )

    def test_first_turn_must_be_user(self):
        with pytest.raises(ValidationError, match="First turn must be from 'user'"):
            TrainingExample(
                contents=[
                    ConversationTurn(role="model", parts=[ContentPart(text="a")]),
                    ConversationTurn(role="user", parts=[ContentPart(text="b")]),
                    ConversationTurn(role="model", parts=[ContentPart(text="c")]),
                ]
            )

    def test_consecutive_same_role_rejected(self):
        with pytest.raises(ValidationError, match="alternate roles"):
            TrainingExample(
                contents=[
                    ConversationTurn(role="user", parts=[ContentPart(text="a")]),
                    ConversationTurn(role="user", parts=[ContentPart(text="b")]),
                    ConversationTurn(role="model", parts=[ContentPart(text="c")]),
                ]
            )

    def test_single_turn_rejected(self):
        with pytest.raises(ValidationError):
            TrainingExample(
                contents=[
                    ConversationTurn(role="user", parts=[ContentPart(text="a")]),
                ]
            )

    def test_multi_turn_valid(self):
        ex = TrainingExample(
            contents=[
                ConversationTurn(role="user", parts=[ContentPart(text="a")]),
                ConversationTurn(role="model", parts=[ContentPart(text="b")]),
                ConversationTurn(role="user", parts=[ContentPart(text="c")]),
                ConversationTurn(role="model", parts=[ContentPart(text="d")]),
            ]
        )
        assert len(ex.contents) == 4

    def test_json_roundtrip(self):
        ex = TrainingExample(
            systemInstruction=SystemInstruction(parts=[ContentPart(text="system")]),
            contents=[
                ConversationTurn(role="user", parts=[ContentPart(text="q")]),
                ConversationTurn(role="model", parts=[ContentPart(text="a")]),
            ],
        )
        json_str = ex.model_dump_json()
        restored = TrainingExample.model_validate_json(json_str)
        assert restored.contents[0].parts[0].text == "q"
