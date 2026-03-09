# Training Data

Drop JSONL training files in this directory. They are **auto-discovered** by the registry — no code changes or manifest updates required.

## How to Add Training Data

1. Create a `.jsonl` file following the Vertex AI format (see `templates/` for examples)
2. Each line is one training example: `systemInstruction` + `contents` (user turn + model turn)
3. The model turn is the **training target** — use human-authored or carefully curated prose
4. Validate: `poetry run python scripts/ft_validate_data.py <your-file.jsonl>`
5. Optionally add a companion `.md` sidecar with YAML frontmatter for metadata

## Naming Convention

The filename (without extension) is the **category** name, used for `--categories` filtering:
- `scene_writing.jsonl` → category `scene_writing`
- `style_editing.jsonl` → category `style_editing`
- `dialogue_subtext.jsonl` → category `dialogue_subtext`

## Optional Sidecar Metadata

Create a `.md` file with the same stem to annotate what the training file teaches:

```yaml
---
teaches:
  - sensory_detail
  - pacing
source: "Hand-crafted examples"
example_count: 3
---

Optional notes about the training data below the frontmatter.
```

## Guidelines

- **Quality over quantity**: 50 excellent examples > 500 mediocre ones
- **Human-authored prose**: Training on LLM output risks model collapse
- **Consistent system instructions**: Keep the same system prompt across examples of the same type
- **Rich user context**: Include scene outlines, character details, tone parameters
- Each example can be up to 131,072 tokens
