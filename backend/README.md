# AI Creative Writing Assistant - Backend

Multi-agent pipeline for structured story generation using LangChain, LangGraph, and Gemini.

## Setup

```bash
poetry install
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY
```

## Running Tests

```bash
poetry run pytest                          # Unit tests only
poetry run pytest -m integration           # Integration tests (requires API key)
```

## Running the Prototype

```bash
poetry run python scripts/run_prototype.py "Your story prompt here"
```
