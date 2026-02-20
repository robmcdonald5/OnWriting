# Backend CLAUDE.md

This file provides backend-specific guidance to Claude when working on the AI Creative Writing Assistant's Python backend. It contains instructions, conventions, and documentation specific to the backend implementation.

---

## Core Directive: Maintain This Document

Similar to the root CLAUDE.md, this document must be kept up-to-date with backend-specific architectural decisions, workflows, and conventions. When making changes that affect backend structure, patterns, or agent implementations, consider if this document needs updating.

---

## Lang Agent Framework Map Documentation

### Overview

The `lang-agent-framework-map.json` file is the **single source of truth** for the agentic architecture of this creative writing system. It documents all agents, their relationships, inputs, outputs, and how they integrate within the LangChain/LangGraph ecosystem.

**Location**: `backend/lang-agent-framework-map.json`

### Critical Maintenance Requirement

**This JSON file MUST be updated whenever:**

1. **Agent Changes**:
   - A new agent is created
   - An existing agent is removed
   - An agent's role or responsibilities change
   - Agent inputs or outputs are modified
   - Sub-agents are added or removed

2. **Relationship Changes**:
   - Data flow between agents is modified
   - New dependencies are created
   - Coordination patterns change
   - Feedback loops are added or removed

3. **Structural Changes**:
   - New departments are created
   - Workflow patterns are modified
   - Integration points change
   - New external dependencies are added

### Update Process

When implementing agent changes:

1. **Before Implementation**: Review the current `lang-agent-framework-map.json` to understand existing relationships
2. **During Implementation**: Keep notes on any deviations from the documented structure
3. **After Implementation**: Update the JSON file to reflect the actual implementation
4. **Validation**: Ensure all relationship references are bidirectional and consistent

### JSON Structure Guide

The JSON file follows this consistent structure:

```json
{
  "framework_version": "semantic version",
  "last_updated": "YYYY-MM-DD",
  "departments": {
    "department_name": {
      "agents": {
        "agent_name": {
          "role": "Clear description",
          "sub_agents": ["list of sub-agents"],
          "inputs": ["expected input types"],
          "outputs": ["produced output types"],
          "relationships": {
            "relationship_type": ["agent_names"]
          }
        }
      }
    }
  }
}
```

### Relationship Types

Standard relationship types to use:
- `coordinates_with`: Bidirectional coordination
- `delegates_to`: Task delegation
- `receives_from`: Data/content reception
- `provides_to`: Data/content provision
- `validates_with`: Validation relationships
- `monitors`: Monitoring relationships
- `stores_via`: Data persistence relationships

### Version Control

- Increment `framework_version` for major structural changes
- Update `last_updated` with every modification
- Consider adding a `changelog` section for significant updates

### Implementation Sync

**Remember**: The JSON map should always reflect the actual implementation, not aspirational design. If you discover the implementation differs from the map during development, update the map immediately.

---

## Prototype Architecture (v0.1.0)

### Overview

The prototype implements a minimal 4-agent pipeline to test the core hypothesis: **structured decomposition through Pydantic schemas produces better creative writing at scale than a single monolithic LLM prompt.**

### Pipeline Flow

```
User Prompt → [Plot Architect] → StoryBrief + CharacterRoster + WorldContext
           → [Beat Outliner]  → StoryOutline (beats + scene outlines)
           → [Scene Writer]   → SceneDraft (raw prose)
           → [Style Editor]   → EditFeedback
               ├── NOT approved & revisions < 2 → back to Scene Writer
               ├── approved OR max revisions    → next scene
               └── last scene complete          → END
```

### Implemented Agents

| Agent | File | LLM Calls | Temperature | Output |
|-------|------|-----------|-------------|--------|
| Plot Architect | `agents/plot_architect.py` | 3 (brief, roster, world) | 0.3 (planning) | StoryBrief, CharacterRoster, WorldContext |
| Beat Outliner | `agents/beat_outliner.py` | 1 | 0.3 (planning) | StoryOutline |
| Scene Writer | `agents/scene_writer.py` | 1 per scene | 0.7 (creative) | SceneDraft |
| Style Editor | `agents/style_editor.py` | 1 per review | 0.3 (analytical) | EditFeedback |

### Key Design Decisions

1. **TypedDict for LangGraph state** (`pipelines/prototype.py:GraphState`): LangGraph works best with TypedDict states for partial update semantics. The Pydantic `PipelineState` in `schemas/pipeline.py` is kept for validation/documentation but GraphState drives the actual pipeline.

2. **Flat-ish schemas for Gemini compatibility**: Structured output via `method="json_schema"` works well with Gemini but deeply nested models can be unreliable. If `StoryOutline` proves too complex for a single call, break Beat Outliner into two calls.

3. **Numeric ToneProfile axes (0.0-1.0)**: Instead of adjectives like "dark" or "formal", the tone profile uses numeric scales. This makes editor feedback unambiguous and measurable.

4. **`prior_scene_summary` for rolling context**: Each `SceneOutline` carries a summary of prior scenes, avoiding the need to pass full prior prose text (which would blow context windows).

5. **Quality score gate (0.7)**: The Style Editor's `EditFeedback.quality_score` determines revision loops. Below 0.7 triggers revision; `max_revisions=2` caps cost.

6. **Advisory over gating for text analysis**: Structural and vocabulary metrics (sentence monotony, lexical diversity, readability) are injected into the Style Editor's LLM evaluation context as advisory information, **not** added as hard gates in `compute_approved()`. This avoids false-positive rejections on creative prose that intentionally breaks "rules" (e.g., a character who speaks in passive voice, or uniform sentence lengths for literary effect). Hard gating can be promoted per-metric once false-positive rates are known.

7. **Text analysis as a package**: `utils/text_analysis/` is a package (not a single file) with sub-modules for each concern (`basics.py`, `slop.py`, `structure.py`, `vocabulary.py`). The `__init__.py` re-exports all public API, so existing imports like `from ai_writer.utils.text_analysis import compute_slop_score` continue to work without changes.

8. **Vendored slop data**: Slop detection uses statistically-derived phrase/word lists from `sam-paech/antislop-sampler`, stored as JSON in `utils/slop_data/`. The data is loaded lazily and cached. Do not hand-edit the JSON files — update them by re-downloading from the upstream source.

### Schema Module Map

All schemas in `src/ai_writer/schemas/`:
- `story.py` — Genre, ToneProfile, ScopeParameters, StoryBrief
- `characters.py` — CharacterRole, CharacterProfile, CharacterRelationship, CharacterRoster
- `world.py` — Location, WorldRule, WorldContext
- `structure.py` — BeatType, EmotionalValence, NarrativeBeat, SceneOutline, ActOutline, StoryOutline
- `writing.py` — SceneDraft, ActDraft
- `editing.py` — EditType, EditSeverity, EditItem, EditFeedback
- `pipeline.py` — PipelineState (Pydantic reference model)

### Running the Prototype

```bash
cd backend
poetry run python scripts/run_prototype.py "Your story prompt"
poetry run pytest                          # Unit tests (121 tests, mocked LLM)
poetry run pytest -m integration           # Integration tests (requires GOOGLE_API_KEY)
```

### Poetry Environment Note

The shell may have `VIRTUAL_ENV` set to an old root-level `.venv`. If `poetry run` fails with "broken virtualenv", prefix commands with `unset VIRTUAL_ENV &&` or use a fresh terminal.

---

## Backend-Specific Conventions

### Agent Pattern

All agents follow the same pattern:
1. Function signature: `def run_<agent_name>(state: dict) -> dict`
2. Extract needed fields from state dict
3. Build system prompt and user context
4. Call LLM (structured or unstructured)
5. Return partial state update dict

### Testing Pattern

- **Unit tests**: Mock LLM calls with `@patch`, verify state field reads and returned keys
- **Pipeline tests**: Test conditional edges and helper nodes with synthetic state
- **Integration tests**: Mark with `@pytest.mark.integration`, require real API key