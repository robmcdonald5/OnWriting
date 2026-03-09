# Validation Data

Validation examples for overfitting detection during fine-tuning. Files here are **auto-discovered** by the registry, separate from training data.

## Purpose

Vertex AI uses validation data to compute `/eval_total_loss` during training. Rising validation loss while training loss drops indicates overfitting.

## How to Add Validation Data

1. Create `.jsonl` files using the same format as training data
2. Use the same category names as training files (e.g., `scene_writing.jsonl`)
3. Validation examples should be **held out** — never duplicated in `training/`
4. A small set (10-20% of training size) is sufficient

## Guidelines

- Same format and schema as training data
- Examples should represent the same distribution as training data
- Do NOT reuse examples from `training/` — the whole point is held-out evaluation
