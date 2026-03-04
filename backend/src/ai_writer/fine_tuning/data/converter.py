"""Convert pipeline outputs to Vertex AI training JSONL format.

Reconstructs training examples from successful pipeline runs:
- System prompt = Scene Writer's system prompt
- User turn = scene outline + context
- Model turn = approved scene prose (training target)
"""

import logging
from pathlib import Path

from ai_writer.fine_tuning.data.schemas import (
    ContentPart,
    ConversationTurn,
    SystemInstruction,
    TrainingExample,
)

logger = logging.getLogger("ai_writer.fine_tuning.data.converter")

# Default system instruction for scene writing training examples
DEFAULT_SYSTEM_INSTRUCTION = (
    "You are a skilled creative fiction writer. Write vivid, engaging prose "
    "that follows the scene outline precisely. Use concrete sensory detail, "
    "varied sentence structure, and authentic character voice. Avoid cliches "
    "and AI-typical constructions."
)


def convert_scene_to_example(
    scene_outline: str,
    approved_prose: str,
    system_instruction: str = DEFAULT_SYSTEM_INSTRUCTION,
    context: str = "",
) -> TrainingExample:
    """Convert a single approved scene into a training example.

    Args:
        scene_outline: The scene outline/prompt given to the Scene Writer.
        approved_prose: The final approved prose output.
        system_instruction: System prompt for the training example.
        context: Additional context (character roster, world, prior scenes).

    Returns:
        A validated TrainingExample.
    """
    user_text = scene_outline
    if context:
        user_text = f"{context}\n\n---\n\n{scene_outline}"

    return TrainingExample(
        systemInstruction=SystemInstruction(
            role="system",
            parts=[ContentPart(text=system_instruction)],
        ),
        contents=[
            ConversationTurn(
                role="user",
                parts=[ContentPart(text=user_text)],
            ),
            ConversationTurn(
                role="model",
                parts=[ContentPart(text=approved_prose)],
            ),
        ],
    )


def convert_pipeline_output(
    pipeline_state: dict,
    system_instruction: str = DEFAULT_SYSTEM_INSTRUCTION,
) -> list[TrainingExample]:
    """Convert a completed pipeline state into training examples.

    Extracts approved scenes from the pipeline output. Each scene that
    passed the Style Editor becomes one training example.

    Args:
        pipeline_state: The final GraphState dict from a pipeline run.
        system_instruction: System prompt for training examples.

    Returns:
        List of TrainingExample objects (one per approved scene).
    """
    examples = []

    scene_drafts = pipeline_state.get("scene_drafts", [])
    story_outline = pipeline_state.get("story_outline")
    character_roster = pipeline_state.get("character_roster")
    world_context = pipeline_state.get("world_context")

    context_parts = []
    if character_roster:
        if hasattr(character_roster, "model_dump_json"):
            roster_text = character_roster.model_dump_json()
        elif isinstance(character_roster, dict):
            import json

            roster_text = json.dumps(character_roster)
        else:
            roster_text = str(character_roster) if character_roster else ""
        if roster_text:
            context_parts.append(f"Characters:\n{roster_text}")
    if world_context:
        if hasattr(world_context, "model_dump_json"):
            world_text = world_context.model_dump_json()
        elif isinstance(world_context, dict):
            import json

            world_text = json.dumps(world_context)
        else:
            world_text = str(world_context) if world_context else ""
        if world_text:
            context_parts.append(f"World:\n{world_text}")

    context = "\n\n".join(context_parts)

    for i, draft in enumerate(scene_drafts):
        prose = getattr(draft, "prose", None) or (
            draft.get("prose") if isinstance(draft, dict) else None
        )
        if not prose:
            continue

        outline_text = ""
        if story_outline:
            scenes = getattr(story_outline, "scenes", None)
            if scenes and i < len(scenes):
                scene = scenes[i]
                if hasattr(scene, "model_dump_json"):
                    outline_text = scene.model_dump_json()
                else:
                    outline_text = str(scene)

        if not outline_text:
            outline_text = f"Scene {i + 1}"

        try:
            example = convert_scene_to_example(
                scene_outline=outline_text,
                approved_prose=prose,
                system_instruction=system_instruction,
                context=context,
            )
            examples.append(example)
        except Exception as e:
            logger.warning("Failed to convert scene %d: %s", i + 1, e)

    logger.info("Converted %d scenes to training examples", len(examples))
    return examples


def write_examples_to_jsonl(
    examples: list[TrainingExample],
    output_path: str | Path,
) -> Path:
    """Write training examples to a JSONL file.

    Args:
        examples: List of validated TrainingExample objects.
        output_path: Path for the output JSONL file.

    Returns:
        Path to the written file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        for example in examples:
            f.write(example.model_dump_json() + "\n")

    logger.info("Wrote %d examples to %s", len(examples), path)
    return path
