# Training Data Templates (Reference Only)

These are **reference examples** demonstrating the correct Vertex AI training data format. They are NOT auto-discovered for training — use `training/` for actual training data.

## Format

Each line is a JSON object representing one conversation:

```json
{
  "systemInstruction": {
    "role": "system",
    "parts": [{"text": "System prompt here"}]
  },
  "contents": [
    {"role": "user", "parts": [{"text": "Input prompt"}]},
    {"role": "model", "parts": [{"text": "Desired output (training target)"}]}
  ]
}
```

## Files

- **`scene_writing.jsonl`** — Scene writing examples (outline → prose)
- **`style_editing.jsonl`** — Style editing examples (weak prose → strong prose)

## Adding Real Training Data

Place your JSONL files in `training/` (one directory up) — they are auto-discovered by the registry. See `training/README.md` for details.

Validate with: `poetry run python scripts/ft_validate_data.py <path.jsonl>`

## Guidelines

- **System instruction**: Keep consistent across examples of the same type
- **User turn**: Include enough context (scene outline, character details, tone)
- **Model turn**: This is the training target — use human-authored prose, not LLM output
- **Quality over quantity**: 200 excellent examples > 1000 mediocre ones
