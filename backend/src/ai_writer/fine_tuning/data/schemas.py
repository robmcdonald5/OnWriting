"""Training data schemas for Vertex AI JSONL format.

Vertex AI expects each JSONL line to be a conversation with:
- systemInstruction (optional): {"role": "system", "parts": [{"text": "..."}]}
- contents: list of turns with role "user" or "model"
- Last "model" turn = training target
"""

from pydantic import BaseModel, Field, model_validator


class ContentPart(BaseModel):
    """A single text part within a conversation turn."""

    text: str = Field(min_length=1)


class ConversationTurn(BaseModel):
    """A single turn in the conversation (user or model)."""

    role: str = Field(description="Either 'user' or 'model'")
    parts: list[ContentPart] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_role(self) -> "ConversationTurn":
        if self.role not in ("user", "model"):
            raise ValueError(f"role must be 'user' or 'model', got '{self.role}'")
        return self


class SystemInstruction(BaseModel):
    """Optional system instruction for the conversation."""

    role: str = Field(default="system")
    parts: list[ContentPart] = Field(min_length=1)


class TrainingExample(BaseModel):
    """A single training example in Vertex AI JSONL format.

    Validates the complete conversation structure:
    - Must have at least one user turn and one model turn
    - Last turn must be from model (training target)
    - Turns must alternate user/model
    """

    systemInstruction: SystemInstruction | None = Field(default=None)
    contents: list[ConversationTurn] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_conversation(self) -> "TrainingExample":
        # min_length=2 on Field already guarantees len >= 2
        if self.contents[-1].role != "model":
            raise ValueError("Last turn must be from 'model' (training target)")

        if self.contents[0].role != "user":
            raise ValueError("First turn must be from 'user'")

        for i in range(1, len(self.contents)):
            if self.contents[i].role == self.contents[i - 1].role:
                raise ValueError(
                    f"Turns must alternate roles, "
                    f"but turns {i - 1} and {i} are both '{self.contents[i].role}'"
                )

        return self
