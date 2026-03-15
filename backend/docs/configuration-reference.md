# Configuration Reference

Comprehensive reference for every configurable setting, hardcoded constant, and potential future config in the creative writing pipeline.

**Source of truth**: This document is derived from the actual source code. When code changes, this doc should be verified and updated.

---

## Section 1: Experiment Settings (PrototypeConfig)

All settings controllable per-experiment via `PrototypeConfig` in `prompts/configs.py`. Set in `scripts/run_prototype.py` as `STORY_CONFIG`. Call `to_prompt_configs()` to fan out into per-agent dicts.

### Story Structure

| Field | Type | Default | Description |
|---|---|---|---|
| `num_acts` | `int` | `1` | Number of acts in the story |
| `scenes_per_act` | `str` | `"2-3"` | Range of scenes per act (string for flexibility) |
| `num_themes` | `str` | `"2-4"` | Range of themes to extract from prompt |
| `min_word_count` | `int` | `800` | Minimum target word count per scene |
| `max_word_count` | `int` | `1200` | Maximum target word count per scene |

### Tone Defaults

Fallback values for SceneWriter/StyleEditor. At runtime, actual values come from `StoryBrief.tone_profile` and override these.

| Field | Type | Default | Description |
|---|---|---|---|
| `default_formality` | `float` | `0.5` | 0.0=casual, 1.0=formal |
| `default_darkness` | `float` | `0.5` | 0.0=lighthearted, 1.0=dark |
| `default_humor` | `float` | `0.3` | 0.0=serious, 1.0=comic |
| `default_pacing` | `float` | `0.5` | 0.0=slow/contemplative, 1.0=fast/action |
| `prose_style` | `str` | `"natural and engaging"` | Freeform prose style description |

### Creative Sampling (Scene Writer only)

Other agents use `Settings.default_temperature` (0.7) with no penalties.

| Field | Type | Default | Description |
|---|---|---|---|
| `creative_temperature` | `float` | `1.3` | LLM temperature for scene writing |
| `frequency_penalty` | `float` | `0.5` | Penalizes repeated tokens |
| `presence_penalty` | `float` | `0.3` | Penalizes tokens that have appeared at all |

### Pipeline Control

| Field | Type | Default | Description |
|---|---|---|---|
| `max_revisions` | `int` | `2` | Maximum editing passes per scene |
| `min_revisions` | `int` | `1` | Guaranteed editing passes per scene (forces polish even if approved) |

### Agent Identity: Role Names

| Field | Type | Default | Description |
|---|---|---|---|
| `story_brief_role` | `str` | `"Plot Architect"` | Role name for StoryBrief generation |
| `character_roster_role` | `str` | `"Casting Director"` | Role name for character creation |
| `world_context_role` | `str` | `"Lore Master"` | Role name for worldbuilding |
| `beat_outliner_role` | `str` | `"Beat Outliner"` | Role name for structural outlining |
| `scene_writer_role` | `str` | `"Scene Writer"` | Role name for prose writing |
| `style_editor_role` | `str` | `"Style Editor"` | Role name for editorial evaluation |

### Agent Identity: Closing Motivations

| Field | Type | Default |
|---|---|---|
| `story_brief_motivation` | `str` | `"Be specific and creative. The brief drives all downstream writing."` |
| `character_roster_motivation` | `str` | `"Make characters feel real and distinct from each other."` |
| `world_context_motivation` | `str` | `"The world should feel consistent and lived-in."` |
| `beat_outliner_motivation` | `str` | `"Be extremely specific. Scene Writers should make ZERO plot decisions — everything\nshould be predetermined in this outline."` |
| `scene_writer_motivation` | `str` | `"Output ONLY the scene prose. No headers, no meta-commentary."` |

### Editor Calibration

| Field | Type | Default | Description |
|---|---|---|---|
| `normalization_guidance` | `str` | `"Score STRICTLY. A score of 3 means 'competent but with clear weaknesses'..."` | Injected into Style Editor prompt to calibrate scoring behavior |

### Slop Detection

| Field | Type | Default | Description |
|---|---|---|---|
| `slop_phrase_penalty_scale` | `float` | `10.0` | Multiplier in `1 - (penalty / words) * scale` ratio formula |
| `slop_word_excess_weight` | `float` | `0.3` | Penalty per excess word occurrence |
| `slop_word_min_severity` | `float` | `0.5` | Minimum severity threshold for word-level scan |
| `slop_word_free_occurrences` | `int` | `1` | Free occurrences before word-level penalty kicks in |

### Prose Structure Thresholds

| Field | Type | Default | Description |
|---|---|---|---|
| `opener_monotony_threshold` | `float` | `0.30` | Flag if >30% of sentences start with same POS |
| `length_cv_threshold` | `float` | `0.30` | Flag if sentence length CV is below this (low variety) |
| `passive_ratio_threshold` | `float` | `0.20` | Flag if >20% of sentences are passive voice |
| `dep_distance_std_threshold` | `float` | `0.50` | Flag if dependency distance std is below this (simple SVO) |

### Vocabulary Thresholds

| Field | Type | Default | Description |
|---|---|---|---|
| `mtld_threshold` | `float` | `60.0` | MTLD below this = low lexical diversity |
| `zipf_threshold` | `float` | `5.5` | Avg Zipf frequency above this = overly common vocabulary |
| `mattr_window` | `int` | `50` | Window size for Moving Average TTR |

### Score Caps (deterministic overrides after LLM scoring)

| Field | Type | Default | Description |
|---|---|---|---|
| `cap_pacing_on_monotony` | `int` | `2` | Hard cap on pacing score when severe monotony detected |
| `severe_opener_threshold` | `float` | `0.45` | Above this opener ratio = severe monotony (cap at 2; mild = cap at 3) |
| `cap_prose_on_slop_count` | `int` | `3` | If confirmed_slop >= this count, cap prose_quality |
| `cap_prose_on_slop_value` | `int` | `2` | Cap prose_quality to this value when slop threshold exceeded |
| `cap_prose_on_low_diversity` | `int` | `3` | Cap prose_quality to this when low vocabulary diversity |
| `cap_prose_on_persistent_slop` | `int` | `1` | Any persistent slop = critical failure (cap to 1) |

### Advisory Penalties

Soft penalty values subtracted from `compute_quality_score()`. Max total: 0.24.

| Field | Type | Default | Description |
|---|---|---|---|
| `penalty_opener_monotony` | `float` | `0.04` | Deducted when opener_monotony flag is True |
| `penalty_length_monotony` | `float` | `0.04` | Deducted when length_monotony flag is True |
| `penalty_passive_heavy` | `float` | `0.02` | Deducted when passive_heavy flag is True |
| `penalty_structural_monotony` | `float` | `0.02` | Deducted when structural_monotony flag is True |
| `penalty_low_diversity` | `float` | `0.04` | Deducted when low_diversity flag is True |
| `penalty_vocabulary_basic` | `float` | `0.02` | Deducted when vocabulary_basic flag is True |
| `penalty_cross_scene_per` | `float` | `0.02` | Deducted per cross-scene repetition |
| `penalty_cross_scene_max` | `int` | `3` | Maximum repetitions counted for penalty (cap at 3 * 0.02 = 0.06) |

---

## Section 2: Environment Settings (Settings / .env)

Deployment-level settings from `config.py` via `pydantic-settings`. Loaded from environment variables and `.env` file.

| Field | Type | Default | Env Var | Description |
|---|---|---|---|---|
| `google_api_key` | `str` | `""` | `GOOGLE_API_KEY` | Google Gemini API key |
| `default_model` | `str` | `"gemini-2.5-flash"` | `DEFAULT_MODEL` | LLM model for all agents |
| `default_temperature` | `float` | `0.7` | `DEFAULT_TEMPERATURE` | Default LLM temperature (non-creative agents) |
| `planning_temperature` | `float` | `0.3` | `PLANNING_TEMPERATURE` | Temperature for planning agents (Plot Architect, Beat Outliner) |
| `langchain_tracing_v2` | `bool` | `True` | `LANGCHAIN_TRACING_V2` | Enable LangSmith tracing |
| `langchain_api_key` | `str` | `""` | `LANGCHAIN_API_KEY` | LangSmith API key |
| `langchain_project` | `str` | `"ai-writer-prototype"` | `LANGCHAIN_PROJECT` | LangSmith project name |

---

## Section 3: Scoring System Constants

Hardcoded in `schemas/editing.py`.

### Dimension Weights

```python
DIMENSION_WEIGHTS: dict[str, float] = {
    "style_adherence": 0.20,
    "character_voice": 0.20,
    "outline_adherence": 0.20,
    "pacing": 0.20,
    "prose_quality": 0.20,
}
```

All equal at 0.20. Key math: all-3s = `(3*0.20*5 - 1) / 3 = 0.67` (below 0.7 threshold).

### Approval Threshold

```python
APPROVE_THRESHOLD = 0.7
```

### Normalization Formula

```python
normalized = (weighted_sum - 1.0) / 3.0  # maps [1, 4] -> [0, 1]
```

### Dimension Score Range

All 5 dimensions constrained to `ge=1, le=4` via Pydantic field validators on both `StyleEditorOutput` and `SceneRubric`.

### SceneRubric Default Scores

All dimension scores default to `2` (on the 1-4 scale).

---

## Section 4: Hardcoded Agent Parameters

Values embedded in agent code that are NOT configurable via `PrototypeConfig` or `Settings`.

### Style Editor (`agents/style_editor.py`)

| Constant | Value | Description |
|---|---|---|
| `_EVAL_TEMPERATURE` | `0.1` | Low temperature for consistent evaluation (LLM-as-judge) |

### Scene Writer (`agents/scene_writer.py`)

| Constant | Value | Description |
|---|---|---|
| `_PROSE_DELIMITER` | `"---PROSE---"` | Separator between planning answers and prose |
| Planning preamble | 4 questions | Forces concrete choices before writing (sensation, physical action, unsaid, 4 opener strategies) |
| Opener POS label map | `{"PRON": "pronouns...", "DET": "articles...", "NOUN": "proper nouns...", "ADV": "adverbs"}` | Human-readable POS labels for revision feedback |
| Dimension score breakpoints | `<=1` = critical, `2` = significant weakness, `3` = room for improvement | Used in revision focus instructions |

### Base Infrastructure (`agents/base.py`)

| Constant | Value | Description |
|---|---|---|
| `_RPM_LIMIT` | `9` | Requests per minute cap (1 under Gemini free tier's 10) |
| `_MAX_RETRIES` | `3` | Maximum 429 retry attempts |
| Rate limiter window | `60` seconds | Sliding window for RPM tracking |
| Rate limiter buffer | `0.5` seconds | Extra wait time after hitting RPM cap |
| Default retry delay | `60.0` seconds | Fallback when server doesn't provide retry_delay |
| Retry delay buffer | `+1.0` second | Added to server-suggested retry_delay |
| `max_retries` on `ChatGoogleGenerativeAI` | `1` | Disables SDK's built-in retry (broken: ignores server retry_delay) |
| `method` for `with_structured_output()` | `"json_schema"` | Gemini structured output method |

---

## Section 5: Hardcoded Text Analysis Parameters

Values in `utils/text_analysis/` that aren't configurable via any config model.

### Slop Detection (`slop.py`)

| Parameter | Value | Description |
|---|---|---|
| Min phrase length | `3` chars | Phrases shorter than 3 characters are skipped |
| Multi-word threshold | `2+` words | `raw_phrase_list` only includes phrases with >= 2 words |
| Punctuation strip chars | `.,!?;:"'()-` | Stripped from words during word-level count |

### Basics (`basics.py`)

| Parameter | Value | Description |
|---|---|---|
| Word count tolerance | `0.25` (25%) | Default `tolerance` parameter in `check_word_count()` |
| Tense consistency threshold | `0.15` (15%) | Default `threshold` parameter in `check_tense_consistency()` |
| spaCy model | `"en_core_web_sm"` | Lazy-loaded and cached; shared by basics and structure |
| Past tense POS tags | `{"VBD", "VBN"}` | Fine-grained spaCy tags for past tense |
| Present tense POS tags | `{"VBP", "VBZ"}` | Fine-grained spaCy tags for present tense |

### Vocabulary (`vocabulary.py`)

| Parameter | Value | Description |
|---|---|---|
| MTLD factor threshold | `0.72` | Passed to `lexicalrichness.mtld(threshold=0.72)` |
| Content word min length | `> 3` chars (so 4+) | Words must be >3 chars AND alpha-only for Zipf scoring |
| Language code | `"en"` | Passed to `wordfreq.zipf_frequency(w, "en")` |
| Minimum word count | `10` | Returns empty result if prose has fewer than 10 words |

### Repetition (`repetition.py`)

| Parameter | Value | Description |
|---|---|---|
| Cross-scene n-gram min | `4` words | Default `min_ngram` parameter |
| Cross-scene n-gram max | `7` words | Default `max_ngram` parameter |
| Zipf common collocation threshold | `5.0` | All words in n-gram must have Zipf > 5.0 to be filtered as common |
| Punctuation strip chars | `.,!?;:"'()-\u2014\u2013` | Stripped from words during n-gram extraction (includes em/en dash) |

### Structure (`structure.py`)

| Parameter | Value | Description |
|---|---|---|
| Top POS distribution display limit | `4` | `summary_lines()` shows top-4 POS openers when flagged |
| Passive voice dep tags | `{"nsubjpass", "auxpass"}` | spaCy dependency labels indicating passive constructions |

### Context (`context.py`)

| Parameter | Value | Description |
|---|---|---|
| Character name part min length | `> 2` chars (so 3+) | Individual name parts must be >2 chars to be allowlisted |
| Theme word min length | `> 3` chars (so 4+) | Theme words must be >3 chars to be allowlisted |

---

## Section 6: Prompt Template Constants

Hardcoded in `prompts/components.py`.

### Tone Axis Breakpoints (Scene Writer)

```
Formality: 0.0-0.3 = contractions, fragments, colloquial
           0.4-0.6 = mixed register, some fragments allowed
           0.7-1.0 = complete sentences, no slang, measured

Darkness:  0.0-0.3 = light stakes, warm imagery
           0.4-0.6 = genuine tension, consequences matter
           0.7-1.0 = threat present, violence possible, danger real

Humor:     0.0-0.2 = no humor
           0.3-0.5 = wry observations, dry wit
           0.6-1.0 = comedic beats, absurdity allowed

Pacing:    0.0-0.3 = long sentences, scene-setting, interiority
           0.4-0.6 = balanced
           0.7-1.0 = short sentences, action-forward, minimal description
```

### Pacing Rubric Thresholds (in EVALUATION_RUBRIC text)

- Sentence length variety: CV > 0.4
- Opener variety: no single opener type > 35%

Note: these are the values stated in the rubric text shown to the LLM. The actual deterministic thresholds used in Python are controlled by `ProseStructureConfig` (default CV: 0.30, opener: 0.30). The rubric text values are aspirational targets communicated to the LLM.

### Banned Constructions (13 patterns)

1. "It was not X, but Y" / "Not X -- just Y" / "No X, no Y -- just Z"
2. Sentences starting with character name + state verb ("Sarah felt...", "John realized...")
3. Emotion announcement phrases ("felt a surge of", "a wave of Y washed over", "couldn't help but feel", "something shifted inside")
4. "Suddenly" as an action initiator
5. Non-"said" dialogue tags (exclaimed, interjected, proclaimed, mused, breathed)
6. Sepia / golden / amber / crimson as default visual register
7. "Testament to" / "tapestry of" / "dance of" / "symphony of"
8. "In that moment" / "in the silence that followed" / "the weight of"
9. "Eyes that held" / "gaze that spoke" / "eyes widened"
10. Ending paragraphs with a thematic one-liner or moral summary

### Craft Principles (9 rules)

1. SHOW emotion through physical action/sensation, never announce it
2. Use concrete sensory detail over abstract description
3. Vary sentence length deliberately (long -> short punch)
4. Never start 3+ consecutive sentences with same POS
5. Dialogue must contain subtext (deflect, evade, change subject)
6. Prefer monosyllabic Anglo-Saxon words over Latinate polysyllables
7. Use "said" for dialogue tags only
8. Trust the reader -- no editorializing or narrator commentary on meaning
9. Open scenes in medias res; end on image/action, not summary

### Evaluation Rubric (5 dimensions x 4 criteria each)

| Dimension | Deterministic Criteria | LLM Criteria |
|---|---|---|
| **Pacing** | (a) Sentence length CV > 0.4, (b) No opener type > 35% | (c) Emotional arc realized, (d) Tension/release rhythm varies |
| **Prose Quality** | (a) Zero confirmed AI-isms, (b) Vocabulary not basic | (c) Sensory/concrete detail used, (d) Imagery is original |
| **Style Adherence** | (none) | (a) Formality match, (b) Darkness match, (c) Humor match, (d) Pacing/tension match |
| **Character Voice** | (none) | (a) Protagonist distinct voice, (b) Natural dialogue, (c) Characters distinguishable, (d) Speech patterns match profiles |
| **Outline Adherence** | (a) Word count within tolerance | (b) Opening hook executed, (c) Closing image executed, (d) Key dialogue beats present |

### Revision/Polish Addendum Templates

- `REVISION_ADDENDUM` — Used when draft NOT approved. Includes: revision count, dimension breakdown, editor notes, focus dimensions, confirmed AI-isms (MANDATORY replacements), structural issues.
- `POLISH_ADDENDUM` — Used when draft approved but forced revision via `min_revisions`. Lighter framing: "preserve strengths, targeted refinements only."

---

## Section 7: External Data Files

Located in `utils/slop_data/`.

| File | Entry Count | Source | Maintenance |
|---|---|---|---|
| `slop_phrases.json` | 517 | Vendored from `sam-paech/antislop-sampler` | Do not hand-edit; re-download from upstream |
| `slop_words.json` | 2000 | Vendored from `sam-paech/slop-forensics` | Do not hand-edit; re-download from upstream |
| `custom_phrases.json` | 21 | Hand-maintained project-specific additions | Edit directly; matches banned constructions |

Loaded lazily on first use, cached for session lifetime. Merged by `_get_compiled_phrases()` in `slop.py` with max-weight-wins for duplicates.

---

## Section 8: Pipeline Graph Structure

Defined in `pipelines/prototype.py`.

### Node Names (7 total)

1. `plot_architect` — Generates StoryBrief, CharacterRoster, WorldContext (3 LLM calls)
2. `beat_outliner` — Generates StoryOutline (1 LLM call)
3. `scene_writer` — Generates SceneDraft (1 LLM call per invocation)
4. `style_editor` — Generates EditFeedback (1 LLM call per invocation)
5. `prepare_revision` — Increments `revision_count`
6. `advance_scene` — Increments `current_scene_index`, resets `revision_count`
7. `mark_complete` — Sets `current_stage = "complete"`

### Edge Topology

```
START -> plot_architect -> beat_outliner -> scene_writer -> style_editor
                                                               |
                                            +------------------+------------------+
                                            |                  |                  |
                                         "revise"          "next_scene"       "complete"
                                            |                  |                  |
                                     prepare_revision    advance_scene      mark_complete
                                            |                  |                  |
                                       scene_writer       scene_writer          END
```

### Conditional Edge Logic (`should_revise_or_advance`)

1. If `revision_count < min_revisions` AND `revision_count < max_revisions` -> `"revise"` (forced)
2. If NOT approved AND `revision_count < max_revisions` -> `"revise"`
3. If `current_scene_index + 1 < total_scenes` -> `"next_scene"`
4. Otherwise -> `"complete"`

### Recursion Limit

```python
config={"recursion_limit": 50}
```

Formula: `2 planning nodes + n_scenes * (3 * max_revisions + 3)`. With 5 scenes, 2 revisions: `2 + 5*9 = 47`.

---

## Section 9: Candidates for Future Configuration

Currently hardcoded values that could reasonably become configurable via `PrototypeConfig`.

| Value | Current Location | Current Value | Rationale |
|---|---|---|---|
| `DIMENSION_WEIGHTS` | `schemas/editing.py` | All `0.20` | Allow non-equal weights (e.g., emphasize prose_quality) |
| `APPROVE_THRESHOLD` | `schemas/editing.py` | `0.7` | Different experiments may want stricter/looser gates |
| `_EVAL_TEMPERATURE` | `agents/style_editor.py` | `0.1` | Experiment with evaluation consistency vs. creativity |
| `planning_temperature` | `config.py` (Settings) | `0.3` | Currently env-level only; should be per-experiment like `creative_temperature` |
| Word count tolerance | `utils/text_analysis/basics.py` | `0.25` | Stricter/looser tolerance per experiment |
| Tense consistency threshold | `utils/text_analysis/basics.py` | `0.15` | Different genres may accept more tense mixing |
| Cross-scene n-gram range | `utils/text_analysis/repetition.py` | `min=4, max=7` | Shorter n-grams catch more; longer = fewer false positives |
| Zipf collocation threshold | `utils/text_analysis/repetition.py` | `5.0` | Tune sensitivity of common phrase filtering |
| MTLD factor threshold | `utils/text_analysis/vocabulary.py` | `0.72` | Standard value but could be experiment-tunable |
| `_RPM_LIMIT` | `agents/base.py` | `9` | Different API tiers have different limits |
| `_MAX_RETRIES` | `agents/base.py` | `3` | More/fewer retries depending on reliability needs |
| `recursion_limit` | `scripts/run_prototype.py` | `50` | Should scale with `num_acts * scenes_per_act * max_revisions` |
| Rubric CV/opener thresholds in text | `prompts/components.py` | `0.4` / `35%` | Currently diverge from `ProseStructureConfig` defaults (0.30/0.30) |

---

## Section 10: Schema Field Reference

Quick-reference tables for all Pydantic schemas flowing through the pipeline. All schemas in `src/ai_writer/schemas/`.

### StoryBrief (`schemas/story.py`) -- 8 fields

| Field | Type | Default | Constraints |
|---|---|---|---|
| `title` | `str` | (required) | `min_length=1` |
| `premise` | `str` | (required) | `min_length=1` |
| `genre` | `Genre` | (required) | Enum: fantasy, sci_fi, literary_fiction, mystery, thriller, romance, horror, historical_fiction |
| `themes` | `list[str]` | `[]` | `min_length=1` |
| `setting_summary` | `str` | `""` | |
| `tone_profile` | `ToneProfile` | defaults | Nested model |
| `scope` | `ScopeParameters` | defaults | Nested model |
| `target_audience` | `str` | `"general adult"` | |

### ToneProfile (`schemas/story.py`) -- 6 fields

| Field | Type | Default | Constraints |
|---|---|---|---|
| `formality` | `float` | `0.5` | `ge=0.0, le=1.0` |
| `darkness` | `float` | `0.5` | `ge=0.0, le=1.0` |
| `humor` | `float` | `0.3` | `ge=0.0, le=1.0` |
| `pacing` | `float` | `0.5` | `ge=0.0, le=1.0` |
| `prose_style` | `str` | `""` | |
| `reference_authors` | `list[str]` | `[]` | |

### ScopeParameters (`schemas/story.py`) -- 4 fields

| Field | Type | Default | Constraints |
|---|---|---|---|
| `target_word_count` | `int` | `3000` | `gt=0` |
| `num_acts` | `int` | `1` | `ge=1, le=5` |
| `scenes_per_act` | `int` | `3` | `ge=1, le=10` |
| `target_scene_word_count` | `int` | `1000` | `gt=0` |

### CharacterProfile (`schemas/characters.py`) -- 10 fields

| Field | Type | Default | Constraints |
|---|---|---|---|
| `character_id` | `str` | (required) | `min_length=1` |
| `name` | `str` | (required) | `min_length=1` |
| `role` | `CharacterRole` | (required) | Enum: protagonist, antagonist, mentor, supporting, love_interest, comic_relief, confidant, foil |
| `description` | `str` | `""` | |
| `personality_traits` | `list[str]` | `[]` | |
| `motivation` | `str` | `""` | |
| `internal_conflict` | `str` | `""` | |
| `backstory_summary` | `str` | `""` | |
| `voice_notes` | `str` | `""` | |
| `speech_patterns` | `list[str]` | `[]` | |

### CharacterRoster (`schemas/characters.py`) -- 2 fields + 2 methods

| Field | Type | Default |
|---|---|---|
| `characters` | `list[CharacterProfile]` | `[]` |
| `relationships` | `list[CharacterRelationship]` | `[]` |

Methods: `get_character(character_id)`, `get_characters_by_role(role)`

### WorldContext (`schemas/world.py`) -- 5 fields

| Field | Type | Default |
|---|---|---|
| `setting_period` | `str` | `""` |
| `setting_description` | `str` | `""` |
| `locations` | `list[Location]` | `[]` |
| `rules` | `list[WorldRule]` | `[]` |
| `key_facts` | `list[str]` | `[]` |

### SceneOutline (`schemas/structure.py`) -- 15 fields

| Field | Type | Default | Constraints |
|---|---|---|---|
| `scene_id` | `str` | (required) | `min_length=1` |
| `act_number` | `int` | (required) | `ge=1` |
| `scene_number` | `int` | (required) | `ge=1` |
| `title` | `str` | `""` | |
| `beat_ids` | `list[str]` | `[]` | |
| `setting` | `str` | `""` | |
| `characters_present` | `list[str]` | `[]` | |
| `pov_character_id` | `str` | `""` | |
| `scene_goal` | `str` | `""` | |
| `emotional_arc` | `str` | `""` | |
| `opening_hook` | `str` | `""` | |
| `closing_image` | `str` | `""` | |
| `key_dialogue_beats` | `list[str]` | `[]` | |
| `prior_scene_summary` | `str` | `""` | |
| `target_word_count` | `int` | `1000` | `gt=0` |

### StoryOutline (`schemas/structure.py`) -- 1 field + 2 computed

| Field | Type | Default |
|---|---|---|
| `acts` | `list[ActOutline]` | `[]` |
| `total_scenes` | `int` | (computed) |
| `total_beats` | `int` | (computed) |

### SceneDraft (`schemas/writing.py`) -- 8 fields

| Field | Type | Default | Constraints |
|---|---|---|---|
| `scene_id` | `str` | (required) | `min_length=1` |
| `act_number` | `int` | (required) | `ge=1` |
| `scene_number` | `int` | (required) | `ge=1` |
| `prose` | `str` | `""` | |
| `word_count` | `int` | `0` | `ge=0` |
| `characters_used` | `list[str]` | `[]` | |
| `scene_summary` | `str` | `""` | |
| `notes_for_editor` | `str` | `""` | |

### StyleEditorOutput (`schemas/editing.py`) -- 10 fields

| Field | Type | Default | Constraints |
|---|---|---|---|
| `dimension_reasoning` | `str` | (required) | First field (critique-before-score ordering) |
| `slop_reasoning` | `str` | `""` | |
| `dismissed_slop` | `list[str]` | `[]` | |
| `style_adherence` | `int` | (required) | `ge=1, le=4` |
| `character_voice` | `int` | (required) | `ge=1, le=4` |
| `outline_adherence` | `int` | (required) | `ge=1, le=4` |
| `pacing` | `int` | (required) | `ge=1, le=4` |
| `prose_quality` | `int` | (required) | `ge=1, le=4` |
| `revision_instructions` | `str` | `""` | |
| `overall_assessment` | `str` | `""` | |

### SceneRubric (`schemas/editing.py`) -- 19 fields + 4 methods

| Field | Type | Default | Source |
|---|---|---|---|
| `word_count_in_range` | `bool` | `True` | Deterministic |
| `tense_consistent` | `bool` | `True` | Deterministic |
| `slop_ratio` | `float` | `1.0` | Deterministic (`ge=0.0, le=1.0`) |
| `style_adherence` | `int` | `2` | LLM (`ge=1, le=4`) |
| `character_voice` | `int` | `2` | LLM (`ge=1, le=4`) |
| `outline_adherence` | `int` | `2` | LLM (`ge=1, le=4`) |
| `pacing` | `int` | `2` | LLM + caps (`ge=1, le=4`) |
| `prose_quality` | `int` | `2` | LLM + caps (`ge=1, le=4`) |
| `top_opener_pos` | `str` | `""` | Deterministic |
| `top_opener_ratio` | `float` | `0.0` | Deterministic (`ge=0.0, le=1.0`) |
| `opener_monotony` | `bool` | `False` | Deterministic (advisory) |
| `length_monotony` | `bool` | `False` | Deterministic (advisory) |
| `passive_heavy` | `bool` | `False` | Deterministic (advisory) |
| `structural_monotony` | `bool` | `False` | Deterministic (advisory) |
| `low_diversity` | `bool` | `False` | Deterministic (advisory) |
| `vocabulary_basic` | `bool` | `False` | Deterministic (advisory) |
| `cross_scene_repetitions` | `int` | `0` | Deterministic |
| `persistent_slop` | `list[str]` | `[]` | Deterministic |
| `dimension_reasoning` | `str` | `""` | LLM |

Methods: `compute_quality_score(penalty_config)`, `has_critical_failure()`, `compute_approved(penalty_config)`, `dimension_summary()`

### EditFeedback (`schemas/editing.py`) -- 9 fields

| Field | Type | Default | Constraints |
|---|---|---|---|
| `scene_id` | `str` | (required) | `min_length=1` |
| `editor_name` | `str` | `"style_editor"` | |
| `edits` | `list[EditItem]` | `[]` | |
| `overall_assessment` | `str` | `""` | |
| `quality_score` | `float` | `0.0` | `ge=0.0, le=1.0` |
| `approved` | `bool` | `False` | |
| `revision_instructions` | `str` | `""` | |
| `confirmed_slop` | `list[str]` | `[]` | |
| `rubric` | `SceneRubric` | defaults | Nested model |

### SceneMetrics (`schemas/editing.py`) -- 6 fields

| Field | Type |
|---|---|
| `scene_id` | `str` |
| `slop_ratio` | `float` |
| `mtld` | `float` |
| `opener_ratio` | `float` |
| `sent_length_cv` | `float` |
| `word_count` | `int` |
