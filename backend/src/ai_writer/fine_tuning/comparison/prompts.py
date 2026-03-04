"""Curated test prompts for A/B comparison.

Organized by category, each prompt mirrors what the Scene Writer receives.
Hardcoded for reproducibility across comparison runs.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TestPrompt:
    """A single test prompt for comparison."""

    id: str
    category: str
    system_prompt: str
    user_prompt: str


# Default system prompt matching Scene Writer persona
_SCENE_SYSTEM = (
    "You are a skilled creative fiction writer. Write vivid, engaging prose "
    "that follows the scene outline precisely. Use concrete sensory detail, "
    "varied sentence structure, and authentic character voice. Avoid cliches "
    "and AI-typical constructions."
)

_STYLE_SYSTEM = (
    "You are an expert prose editor specializing in literary fiction. Revise "
    "the given passage to improve prose quality while preserving the author's "
    "voice and intent. Focus on eliminating cliches, strengthening sensory "
    "detail, varying sentence structure, and tightening language."
)

# --- Scene Writing Prompts ---

SCENE_WRITING_PROMPTS = [
    TestPrompt(
        id="scene_01",
        category="scene_writing",
        system_prompt=_SCENE_SYSTEM,
        user_prompt=(
            "Scene: A woman returns to her childhood home after 20 years to "
            "find it converted into a coffee shop. She orders a drink and sits "
            "where the kitchen table used to be. Tone: bittersweet, restrained. "
            "POV: third-person limited."
        ),
    ),
    TestPrompt(
        id="scene_02",
        category="scene_writing",
        system_prompt=_SCENE_SYSTEM,
        user_prompt=(
            "Scene: Two soldiers from opposing sides meet at a river crossing "
            "at dawn. Neither has ammunition left. They share a canteen of "
            "water. Tone: quiet exhaustion, anti-war. POV: third-person "
            "omniscient, alternating focus."
        ),
    ),
    TestPrompt(
        id="scene_03",
        category="scene_writing",
        system_prompt=_SCENE_SYSTEM,
        user_prompt=(
            "Scene: A marine biologist discovers that the whale song she's "
            "been recording contains a repeating mathematical pattern. She "
            "works alone on a research vessel at night. Tone: wonder mixed "
            "with unease. POV: first person."
        ),
    ),
]

# --- Opening Sentence Prompts ---

OPENING_PROMPTS = [
    TestPrompt(
        id="open_01",
        category="opening",
        system_prompt=_SCENE_SYSTEM,
        user_prompt=(
            "Write the opening paragraph (3-5 sentences) of a literary "
            "thriller set in a decaying resort town in winter. Establish "
            "atmosphere and a sense that something is wrong without stating "
            "it directly. First person POV."
        ),
    ),
    TestPrompt(
        id="open_02",
        category="opening",
        system_prompt=_SCENE_SYSTEM,
        user_prompt=(
            "Write the opening paragraph (3-5 sentences) of a literary novel "
            "about a translator who discovers a language that has no word for "
            "'I'. Third person. Tone: cerebral, precise."
        ),
    ),
]

# --- Style Matching Prompts ---

STYLE_MATCHING_PROMPTS = [
    TestPrompt(
        id="style_01",
        category="style_matching",
        system_prompt=_SCENE_SYSTEM,
        user_prompt=(
            "Write a 200-word passage in the style of Cormac McCarthy: sparse "
            "punctuation, no quotation marks for dialogue, biblical cadence, "
            "landscape as character. Scene: two men walk through a burned "
            "forest at dusk."
        ),
    ),
    TestPrompt(
        id="style_02",
        category="style_matching",
        system_prompt=_SCENE_SYSTEM,
        user_prompt=(
            "Write a 200-word passage in the style of Ursula K. Le Guin: "
            "anthropological precision, quiet authority, gender as fluid "
            "concept. Scene: a visitor arrives at a village that has no concept "
            "of ownership."
        ),
    ),
]

# --- Tone Adherence Prompts ---

TONE_ADHERENCE_PROMPTS = [
    TestPrompt(
        id="tone_01",
        category="tone_adherence",
        system_prompt=_SCENE_SYSTEM,
        user_prompt=(
            "Write a scene where a character receives devastating news. "
            "CONSTRAINT: The tone must be darkly comic throughout. The "
            "character processes grief through inappropriate humor. "
            "200-300 words. Third person limited."
        ),
    ),
    TestPrompt(
        id="tone_02",
        category="tone_adherence",
        system_prompt=_SCENE_SYSTEM,
        user_prompt=(
            "Write a scene of great violence (a bar fight) in a tone that is "
            "completely clinical and detached, as if narrated by a forensic "
            "report. 200-300 words. No emotional language."
        ),
    ),
]

# --- Style Editing Prompts ---

STYLE_EDITING_PROMPTS = [
    TestPrompt(
        id="edit_01",
        category="style_editing",
        system_prompt=_STYLE_SYSTEM,
        user_prompt=(
            "Edit this passage:\n\n"
            "John walked into the room and immediately felt a sense of dread. "
            "The air was thick with tension. Everyone looked at him with eyes "
            "full of suspicion. He swallowed hard and tried to act normal, but "
            "his hands were shaking like leaves in the wind. He knew this "
            "moment would define the rest of his life."
        ),
    ),
    TestPrompt(
        id="edit_02",
        category="style_editing",
        system_prompt=_STYLE_SYSTEM,
        user_prompt=(
            "Edit this passage:\n\n"
            "The ancient forest whispered its secrets to those who dared to "
            "listen. Moonlight filtered through the canopy, casting ethereal "
            "patterns on the moss-covered ground. Elena felt a deep connection "
            "to nature as she wandered deeper into the woods, her soul "
            "resonating with the primal energy that pulsed through every "
            "living thing around her."
        ),
    ),
]

# All prompts indexed by category
PROMPT_CATEGORIES: dict[str, list[TestPrompt]] = {
    "scene_writing": SCENE_WRITING_PROMPTS,
    "opening": OPENING_PROMPTS,
    "style_matching": STYLE_MATCHING_PROMPTS,
    "tone_adherence": TONE_ADHERENCE_PROMPTS,
    "style_editing": STYLE_EDITING_PROMPTS,
}


def get_prompts(categories: list[str] | None = None) -> list[TestPrompt]:
    """Get test prompts, optionally filtered by category.

    Args:
        categories: List of category names, or None/["all"] for all prompts.

    Returns:
        List of TestPrompt objects.
    """
    if categories is None or "all" in categories:
        prompts = []
        for cat_prompts in PROMPT_CATEGORIES.values():
            prompts.extend(cat_prompts)
        return prompts

    prompts = []
    for cat in categories:
        if cat in PROMPT_CATEGORIES:
            prompts.extend(PROMPT_CATEGORIES[cat])
    return prompts
