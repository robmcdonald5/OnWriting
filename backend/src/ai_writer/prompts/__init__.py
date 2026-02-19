"""Prompt templates for agents.

Public API:
    - Builders: functions that compose system prompts from components + config
    - Configs: Pydantic models defining the configurable surface per agent
    - REVISION_ADDENDUM: conditional template appended by scene writer
"""

from ai_writer.prompts.builders import (
    build_beat_outliner_prompt,
    build_character_roster_prompt,
    build_scene_writer_prompt,
    build_story_brief_prompt,
    build_style_editor_prompt,
    build_world_context_prompt,
)
from ai_writer.prompts.components import REVISION_ADDENDUM
from ai_writer.prompts.configs import (
    BeatOutlinerPromptConfig,
    CharacterRosterPromptConfig,
    PrototypeConfig,
    SceneWriterPromptConfig,
    StoryBriefPromptConfig,
    StyleEditorPromptConfig,
    WorldContextPromptConfig,
)

__all__ = [
    # Builders
    "build_story_brief_prompt",
    "build_character_roster_prompt",
    "build_world_context_prompt",
    "build_beat_outliner_prompt",
    "build_scene_writer_prompt",
    "build_style_editor_prompt",
    # Configs
    "PrototypeConfig",
    "StoryBriefPromptConfig",
    "CharacterRosterPromptConfig",
    "WorldContextPromptConfig",
    "BeatOutlinerPromptConfig",
    "SceneWriterPromptConfig",
    "StyleEditorPromptConfig",
    # Components
    "REVISION_ADDENDUM",
]
