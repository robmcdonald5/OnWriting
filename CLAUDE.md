# CLAUDE.md

This file provides guidance to Claude when working on the AI Creative Writing Assistant. It outlines the project architecture, technology stack, and the development workflow.

## Project Overview

This project is an **AI Creative Writing Assistant** that uses a multi-department agentic framework (Architects, Constructors, Writers, Editors).

The development strategy is to first build a robust, production-ready **Python Backend** that contains the entire agentic system. This backend will then be exposed via a REST API. Subsequently, a **SvelteKit Frontend** will be developed to interact with the backend API, providing the user interface.

---

## Core Directive: Maintain This Document 📜

After any significant code change, architectural decision, or workflow modification, you must pause and consider if this `CLAUDE.md` file needs to be updated to reflect the change.

### Decision Framework for Updates

* **Global Rules**: If the change affects the overall project structure, high-level strategy, or cross-cutting concerns, the update belongs in this **root `CLAUDE.md` file**.
* **Local Rules**: If the change introduces rules or conventions that are specific to a single directory (e.g., a new required format for all agents in `src/ai_writer/agents/`), you should propose creating a **new, more specific `CLAUDE.md` file inside that subdirectory**.

When bugs are fixed, complicated algorithms or methods are implemented, general misteps are addressed. Consider if it is a good idea to document these changes in the root CLAUDE.md file or to document it in a new or existing CLAUDE.md within a subfolder. The purpose of this is to make sure critical big picture ideas are continually documented in the root CLAUDE.md, but smaller, but still important architecture decisions and changes are still kept track of without cluttering the root CLAUDE.md document.
If you believe an update is needed, please state the proposed change and its location (root or sub-folder) and ask for my approval to update or add documentation.

---

## Technology Stack

This project is composed of two primary services: a Python backend and a SvelteKit frontend.

### Backend Stack (Python)

* **Language**: Python
* **Agent Framework**: **LangChain** (for core agent components)
* **Orchestration Framework**: **LangGraph** (to manage complex, cyclical agent workflows)
* **Web API Framework**: **FastAPI** or **LangServe** (to expose the agentic system via a REST API)
* **Data Schemas**: **Pydantic** (for input/output schemas and data validation)
* **Configuration**: **`pydantic-settings`** (for managing environment variables and secrets)
* **Debugging & Tracing**: **LangSmith** (for observing, testing, and evaluating agent traces)
* **Specialized Tools**: 
    * **LangExtract**: For high-precision, auditable structured data extraction.
    * **spaCy**: For fast, deterministic linguistic tasks (e.g., NER, sentence splitting).
* **Testing Framework**: **pytest**

### Frontend Stack (SvelteKit)

* **Framework**: **SvelteKit5** + **TailwindCSS4**
* **Language**: TypeScript
* **Package Manager**: `npm`

---

## Professional Setup & Workflow

This section outlines the professional standards for dependency management, code quality, and automation to be used in this repository.

### Dependency Management (Python)

This project will use **Poetry** for Python dependency management. It uses the `pyproject.toml` file to define dependencies and creates a `poetry.lock` file to ensure deterministic, reproducible builds. The `requirements.txt` file should not be used.

* **Installation**: To set up the environment, run `poetry install`.
* **Adding a new library**: Use `poetry add <package-name>`.
* **Adding a dev library**: Use `poetry add <package-name> --group dev`.
* **Running scripts**: Execute scripts within the managed environment using `poetry run <command>`.

### Code Quality & Formatting (Python)

A strict, automated code quality process will be enforced. These tools should be configured in `pyproject.toml`.

* **Formatter**: **Black** will be used for uncompromising code formatting.
* **Linter**: **Ruff** will be used as the primary linter for its speed and comprehensive rule set, replacing older tools like flake8 and pylint.
* **Import Sorting**: **isort** will be used to automatically organize imports.

### Automated Workflows (CI with GitHub Actions)

The `.github/workflows/` directory will contain CI (Continuous Integration) pipelines. A primary workflow will be configured to run on every pull request against the `main` branch. This workflow must perform two critical jobs:
1.  **Lint & Format Check**: Run `ruff` and `black --check` to ensure all code adheres to the quality standards.
2.  **Run Tests**: Run the complete `pytest` suite to ensure no regressions have been introduced.

A pull request will be blocked from merging if either of these jobs fails.

### Git & Commit Conventions

This project will follow the **Conventional Commits** specification. This creates a clean and readable commit history.
* **Examples**: `feat: add LoreMaster agent`, `fix: correct Pydantic schema for story brief`, `docs: update CLAUDE.md with CI workflow`.

---

## Directory Structure

### `backend/` (Python Production Service)

backend/
├── notebooks/              # Jupyter notebooks for interactive testing and exploration
├── scripts/                # Standalone scripts to run specific pipelines from the CLI
├── src/
│   └── ai_writer/          # The main source package for the application
│       ├── api/            # FastAPI/LangServe API definitions and routes
│       ├── agents/         # Individual agent logic (e.g., Chief-Architect.py)
│       ├── core/           # Core components (e.g., graph state, main orchestrator)
│       ├── pipelines/      # LangGraph definitions chaining agents together
│       ├── prompts/        # Directory for storing and managing prompt templates
│       ├── config.py       # Pydantic-settings configuration loading
│       └── main.py         # Main application entrypoint to start the API server
├── tests/
│   ├── agents/             # Unit tests for agents
│   └── api/                # Tests for the API endpoints
├── .env                    # Local environment variables
├── .env.example            # Example environment file for contributors
├── pyproject.toml          # Project definition and dependency management (Poetry)
├── poetry.lock             # For deterministic builds
├── Dockerfile              # Instructions to containerize the Python backend
└── README.md

### `frontend/` (SvelteKit UI)

frontend/
├── src/
│   ├── lib/
│   │   ├── client/       # Client-side components and utilities
│   │   └── server/       # Server-side utilities and API handlers that call the Python backend
│   ├── routes/
│   │   └── +layout.svelte  # Root layout, imports global CSS
│   ├── app.css           # Global stylesheet with Tailwind directives
│   └── app.html          # Main HTML app shell
├── static/                 # Static assets
├── postcss.config.js       # PostCSS configuration
├── svelte.config.js        # SvelteKit configuration
└── tailwind.config.js      # Tailwind CSS configuration
└── package.json

---

## Phased Development Workflow

The development process is sequential, focusing on building a robust backend first, then creating the user-facing frontend.

### Phase 1: Core Agent Development (**THIS IS THE CURRENT PHASE**)
**Goal**: Build and individually test the core agents that form the "Brain" (Architects, Constructors) of the application.
1.  Follow a test-driven development (TDD) approach using `pytest`. Write a test for an agent first, then write the agent logic to make the test pass.
2.  Define clear Pydantic models for each agent's inputs and outputs.
3.  Use **LangSmith** from day one to trace and debug agent behavior during tests.
4.  Focus on perfecting each agent in isolation before worrying about connecting them.

### Phase 2: Graph Integration & Orchestration
**Goal**: Assemble the individual agents into a functional, multi-step pipeline using LangGraph.
1.  Define the master `State` Pydantic model for the graph.
2.  Wire the tested agents together as nodes in a LangGraph workflow inside the `pipelines/` directory.
3.  Implement conditional logic and cycles (e.g., `Editor` agent sends work back to a `Writer` agent for revision).
4.  Continue using **LangSmith** to visualize and debug the entire graph's flow.

### Phase 3: API Exposure
**Goal**: Expose the completed LangGraph pipeline to the outside world via a REST API.
1.  Use **LangServe** or **FastAPI** to create API endpoints in the `api/` directory.
2.  A primary endpoint might be `POST /generate/story`, which takes a user prompt and initiates the LangGraph pipeline.
3.  For long-running tasks, implement a job queue pattern (e.g., with Celery & Redis) to immediately return a `job_id`.
4.  Create status endpoints (e.g., `GET /jobs/{job_id}/status`) for the frontend to poll.

### Phase 4: Frontend Development & Integration
**Goal**: Build the SvelteKit user interface and connect it to the Python backend API.
1.  Develop the SvelteKit components for the UI.
2.  Write TypeScript functions in `frontend/src/lib/server/` to make `fetch` calls to the Python REST API.
3.  Manage application state using Svelte Stores.
4.  Ensure end-to-end functionality from the user clicking a button in the UI to the Python backend completing the agentic workflow.

---

## Agent Invocation Framework: General Contractor vs. Subcontractors

This framework defines when to use the main, primary Claude session versus a specialized agent.

### The Main Session: The "General Contractor"

The main conversational session with Claude is the "General Contractor." It holds the full project context and is the default for all development tasks.

* **Primary Worker**: The main session should perform big picture changes to the repository.
* **Research Agents**: If research on a task is considered to be a good idea by Claude or the user explicitly states research needs to be done, you should check if one ofs the research agents is meant for this task; otherwise, let the main session do the research.
* **Developer Agents**: If there is a coding task that needs to be done, it should first be considered how much of the codebase this code change/addition/removal will impact. If the impact is large any touches many code files at once, the main session should probably do this coding task. If the impact is smaller in scope consider tasking a relevant developer agent. When the developer agent is done outputting, the main session should analyze agents output and either approve the change or raise concerns to the user if any problems are detected with what the agent wrote. At this point the user will tell the main agent to take over the task or have the agent try again maybe with extra added context.

* **When to Invoke a Developer Agent**: Below is a good framework for reasons to call upon agents:
    1.  **Repetitive & Boilerplate-Heavy**: Generating a new Pydantic model or a `pytest` file structure is an example of this.
    2.  **Low-Context & Rule-Based**: The task can be completed correctly without knowing the full project history.
    3.  **Requires High Precision**: The task demands a very specific format generally accepted by experts to not change much between many code files.

---

## Agent Generation Workflow

This project includes a sophisticated agent generation system to create specialized developer and research agents efficiently.

### Agent Generator Location & Usage

* **Agent Generator**: `.claude/agents/agent-generator.md`
* **Templates**: `.claude/agents/agent-template-developer.md` and `.claude/agents/agent-template-researcher.md`
* **Existing Agents**: `.claude/agents/` contains pre-built specialized agents

### Streamlined Agent Creation Process

**When to Create New Agents:**
- Task will be repeated 5+ times with consistent patterns
- Requires specialized domain knowledge (e.g., specific framework)
- Benefits from template-driven consistency

**Efficient Invocation Pattern:**
```
Use Task tool with agent-generator:
"I am the agent-generator agent. Create a new [technology]-[type] agent..."
```

**Agent Types:**
- **Research Agents**: Documentation gathering, best practices (model: sonnet, color: green)
- **Developer Agents**: Code implementation, boilerplate generation (model: opus, color: red)

**Naming Convention:**
- Research: `[technology]-researcher` (e.g., `fastapi-researcher`)
- Developer: `[technology]-developer` (e.g., `pydantic-developer`)

### Quality Standards for New Agents

New agents must include:
- 3 realistic usage examples in description
- 5-7 specific capabilities for the technology
- Development principles (developer agents) or search strategies (research agents)
- Customized output format while maintaining template structure
- No overlap with existing agents in `.claude/agents/`