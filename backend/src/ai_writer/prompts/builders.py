"""Prompt composition functions — assemble components + config into system prompts.

Each builder takes a config model and returns a fully formatted system prompt
string. Agents call these instead of maintaining inline string constants.

The returned strings are used directly as the "system" message content in
the agent's LLM invocation — no ChatPromptTemplate wrapper needed since
agents already build message lists as plain dicts.
"""

from ai_writer.prompts.components import (
    BEAT_OUTLINER_GUIDELINES,
    CHARACTER_ROSTER_GUIDELINES,
    EVALUATION_RUBRIC,
    ROLE_IDENTITY,
    SCENE_WRITER_GUIDELINES,
    STORY_BRIEF_GUIDELINES,
    TASK_STATEMENTS,
    WORLD_CONTEXT_GUIDELINES,
)
from ai_writer.prompts.configs import (
    BeatOutlinerPromptConfig,
    CharacterRosterPromptConfig,
    SceneWriterPromptConfig,
    StoryBriefPromptConfig,
    StyleEditorPromptConfig,
    WorldContextPromptConfig,
)


def build_story_brief_prompt(config: StoryBriefPromptConfig) -> str:
    """Compose the Plot Architect (StoryBrief) system prompt."""
    parts = [
        ROLE_IDENTITY.format(role_name=config.role_name),
        TASK_STATEMENTS["story_brief"],
        "",
        STORY_BRIEF_GUIDELINES.format(
            num_themes=config.num_themes,
            num_acts=config.num_acts,
            scenes_per_act=config.scenes_per_act,
            min_word_count=config.min_word_count,
            max_word_count=config.max_word_count,
        ),
        "",
        config.closing_motivation,
    ]
    return "\n".join(parts)


def build_character_roster_prompt(config: CharacterRosterPromptConfig) -> str:
    """Compose the Plot Architect (CharacterRoster) system prompt."""
    parts = [
        ROLE_IDENTITY.format(role_name=config.role_name),
        TASK_STATEMENTS["character_roster"],
        "",
        CHARACTER_ROSTER_GUIDELINES,
        "",
        config.closing_motivation,
    ]
    return "\n".join(parts)


def build_world_context_prompt(config: WorldContextPromptConfig) -> str:
    """Compose the Plot Architect (WorldContext) system prompt."""
    parts = [
        ROLE_IDENTITY.format(role_name=config.role_name),
        TASK_STATEMENTS["world_context"],
        "",
        WORLD_CONTEXT_GUIDELINES,
        "",
        config.closing_motivation,
    ]
    return "\n".join(parts)


def build_beat_outliner_prompt(config: BeatOutlinerPromptConfig) -> str:
    """Compose the Beat Outliner system prompt."""
    parts = [
        ROLE_IDENTITY.format(role_name=config.role_name),
        TASK_STATEMENTS["beat_outliner"],
        "",
        BEAT_OUTLINER_GUIDELINES,
        "",
        config.closing_motivation,
    ]
    return "\n".join(parts)


def build_scene_writer_prompt(config: SceneWriterPromptConfig) -> str:
    """Compose the Scene Writer system prompt (without revision addendum)."""
    parts = [
        ROLE_IDENTITY.format(role_name=config.role_name),
        TASK_STATEMENTS["scene_writer"],
        "",
        SCENE_WRITER_GUIDELINES.format(
            formality=config.formality,
            darkness=config.darkness,
            humor=config.humor,
            pacing=config.pacing,
            prose_style=config.prose_style,
            target_word_count=config.target_word_count,
        ),
        "",
        config.closing_motivation,
    ]
    return "\n".join(parts)


def build_style_editor_prompt(config: StyleEditorPromptConfig) -> str:
    """Compose the Style Editor system prompt."""
    parts = [
        ROLE_IDENTITY.format(role_name=config.role_name),
        TASK_STATEMENTS["style_editor"],
        "",
        EVALUATION_RUBRIC.format(
            formality=config.formality,
            darkness=config.darkness,
            humor=config.humor,
            pacing=config.pacing,
            normalization_guidance=config.normalization_guidance,
        ),
    ]
    return "\n".join(parts)
