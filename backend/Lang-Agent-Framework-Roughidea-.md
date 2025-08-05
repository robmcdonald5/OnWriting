# AI Creative Writing Agentic Framework

## Department 1: Architects
*"Define the vision & scope"*

### Plot Architect
- **Role**: Mission control that never writes text itself, but spins up tasks and refines the brief via back-and-forth with the user
- **Enhancements**:
 - **Tone & Theme Analyst** sub-agent to capture desired mood (e.g. "gritty sci-fi" vs. "lighthearted fantasy")
 - **Prompt Optimizer** that tailors system instructions for downstream agents (helping ensure consistent voice across all steps)

### Lore Master
- **Role**: Centralizes worldbuilding
- **Enhancements**:
 - Split into **Setting Designer** (geography, cultures, history) and **Mechanics Designer** (magic/tech systems, rules)
 - **World-Consistency Agent** that cross-checks new lore entries against existing world rules

### Casting Director
- **Role**: High-level character roster
- **Enhancements**:
 - **Relationship Graph Builder**: plots character interconnections (alliances, rivalries)
 - **Archetype Analyst**: tags each character (e.g. "mentor," "anti-hero") to guide tone

### Scope Master
- **Role**: Manages length, depth, and pacing parameters
- **Enhancements**:
 - Clarify its remit: e.g. "Total word count," "Acts vs. Scenes," "Target audience reading level"
 - **Scope Change Mediator**: when the user requests a pivot (e.g. "make it shorter"), updates all downstream plans

## Department 2: Constructors
*"Sub-task specialists invoked by other agents"*

### Beat Outliner
Breaks high-level summary into narrative beats or key scenes

### Research Assistant
Fetches or simulates domain-specific knowledge (historical facts, sci-fi tech tropes)

### Fact Checker
Validates internal consistency (dates, names, tech metaphors)

### Memory Manager
Handles storage & retrieval of summaries, lore docs, character sheets—possibly via a vector database

### Template Generator
Produces structured templates (chapter templates, scene checklists) for Writers to fill in

## Department 3: Writers
*"Generate raw story material"*

### Act Writer
- **Suggestion**: expose configurable parameters (tone shifts, climax placement) so that each act outline can be fine-tuned

### Scene/Chapter Writer
- Great to have a rolling "trail of memory" of prior summaries
- **Enhancement**: consider an intermediate **Scene Architect** that drafts scene-by-scene bullet points before the full prose is written

### Act Summarizer
Reinforces long-range coherence by folding act summaries back into the Memory Manager

## Department 4: Editors
*"Quality-assurance & refinement"*

### Editor-in-Chief
Coordinates specialist editors in a fixed pipeline

### Continuity Editor
Checks against world lore and prior summaries

### Character Context Editor
Ensures characters' choices and dialogue remain on-brand

### Style Editor
Polishes grammar, syntax, and prose flair without altering plot or character

### Act Editor
Big-picture pass on pacing, narrative arcs, and thematic resonance

## Cross-Cutting & Support Agents

### Task Orchestrator (Pipeline Manager)
Oversees the end-to-end flow—routes tasks from Architects → Constructors → Writers → Editors

### Error/Exception Handler
Detects when an agent's output goes off-rails (e.g. context window overflow) and retries or reroutes

### Metrics & Logging Agent
Tracks progress (e.g. word counts, number of iterations) and surfaces logs for user review

### Feedback Collector
Periodically prompts the user for high-level feedback ("Is the tone working for you?") to adjust system prompts

### Publishing Agent
At project end, compiles the final manuscript, meta-data, cover art, and export formats (e.g. EPUB, PDF)