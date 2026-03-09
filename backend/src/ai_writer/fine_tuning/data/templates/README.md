# Training Data Templates

Example JSONL files demonstrating the correct Vertex AI training data format.

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
    {"role": "model", "parts": [{"text": "Desired output (training target)"}}
  ]
}
```

## Files

- **`scene_writing.jsonl`** — Scene writing examples (outline → prose). Use as a template for training the Scene Writer on specific writing styles.
- **`style_editing.jsonl`** — Style editing examples (weak prose → strong prose). Use as a template for training on prose revision tasks.

## Adding Real Training Data

1. Copy one of the template files as a starting point
2. Replace mock examples with real pipeline outputs (use `scripts/ft_convert_outputs.py`)
3. Validate with `scripts/ft_validate_data.py`
4. Aim for 100-500 examples for creative writing tasks
5. Each example can be up to 131,072 tokens

## Guidelines

- **System instruction**: Keep consistent across examples of the same type
- **User turn**: Include enough context (scene outline, character details, tone)
- **Model turn**: This is the training target — use your best, editor-approved prose
- **Quality over quantity**: 200 excellent examples > 1000 mediocre ones
- Avoid training on prose that still has slop or structural issues
