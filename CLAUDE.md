# CLAUDE.md

This file provides guidance to Claude when working on the AI Creative Writing Assistant. It outlines the project architecture, technology stack, and the development workflow.

## Project Overview

This project is an **AI Creative Writing Assistant** that uses a multi-department agentic framework (Architects, Constructors, Writers, Editors).

The development strategy is two-phased:
1.  **AI Core Prototyping (Python)**: The initial agentic logic will be rapidly developed and tested in Python to leverage its mature AI ecosystem.
2.  **Production Implementation (TypeScript)**: Once the core logic is validated, it will be ported to TypeScript to build a robust, scalable backend for the final SvelteKit application.

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

This project uses two distinct stacks for its two development phases.

### Phase 1: AI Core Prototyping

* **Language**: Python
* **Agent Framework**: **LangChain** (the Python library), (input output schema for agents will use Pydantic models)
* **Orchestration Framework**: **LangGraph** to manage complex, cyclical agent workflows.
* **Testing Framework**: **pytest**

### Phase 2: Production Backend & Frontend

* **Language**: TypeScript
* **Runtime**: Node.js
* **Package Manager**: `npm`
* **Agent Framework**: **LangChain.js** (`@langchain/core`, `@langchain/openai`, etc.)
* **Testing Framework**: **Vitest** for unit and integration testing.
* **Execution Tool**: **`tsx`** to execute `.ts` files directly during development.
* **Frontend Framework**: **SvelteKit5** + **TailwindCSS4**

---

## Directory Structure

### `backend-python-prototype/`

MVP product development directory for initial development of agents in LangChain Python.

### `backend/` (TypeScript)

---

Python MVP development backend:

backend-python-prototype/
├── notebooks/              # Jupyter notebooks for interactive testing and exploration
├── scripts/                # Standalone scripts to run specific pipelines from the CLI
├── src/
│   └── ai_writer/          # The main source package for your application
│       ├── agents/         # Individual agent logic (e.g., Chief-Architect.py, XyZConstructor.py, etc..)
│       ├── core/           # Core components (e.g., graph state, main orchestrator)
│       ├── pipelines/      # LangGraph definitions chaining agents together
│       ├── prompts/        # Directory for storing and managing prompt templates
│       ├── utils/          # Shared utility functions
│       └── __init__.py     # Makes `ai_writer` a Python package
├── tests/
│   ├── agents/             # Unit tests for agents
│   └── __init__.py
├── .env                    # Local environment variables
├── .gitignore
├── pyproject.toml          # Modern Python project definition and dependency management
└── README.md

---

The final production backend:

backend/
├── dist/                   # Compiled JavaScript output from the build process
├── src/
│   ├── api/                # HTTP routes and controllers (e.g., Express, Fastify)
│   │   └── v1/
│   │       └── stories.routes.ts
│   ├── agents/             # Individual agent logic (e.g., loreMaster.ts)
│   ├── core/               # Core components (e.g., taskOrchestrator.ts)
│   ├── pipelines/          # Multi-agent chains and workflows
│   ├── lib/                # Shared utilities, types, and prompt templates
│   └── server.ts           # Server entry point: initializes and starts the server
├── tests/
│   ├── agents/             # Unit tests for agents
│   └── pipelines/          # Integration tests for pipelines
├── .env                    # Local environment variables (secrets, API keys)
├── .env.example            # Example environment file for contributors
├── .eslintrc.js            # ESLint configuration for code quality
├── .prettierrc             # Prettier configuration for code formatting
├── Dockerfile              # Instructions for building a deployable container image
├── package.json
└── tsconfig.json

---

## Frontend Directory Structure

When working in the `frontend/` directory, please adhere to this standard SvelteKit structure:

frontend/
├── src/
│   ├── lib/
│   │   ├── client/       # Client-side components and utilities
│   │   └── server/       # Server-side utilities and API handlers
│   ├── routes/
│   │   └── +layout.svelte  # Root layout, imports global CSS
│   ├── app.css           # Global stylesheet with Tailwind directives
│   └── app.html          # Main HTML app shell
├── static/                 # Static assets
├── postcss.config.js       # PostCSS configuration
├── svelte.config.js        # SvelteKit configuration
└── tailwind.config.js      # Tailwind CSS configuration

---

## Phased Agent Development Workflow

The primary development loop is **test-driven**. We will build the system in phases, starting with a simple, end-to-end "walking skeleton" and progressively adding complexity.

### Phase 1: Core Agentic Writing Pipeline (Architects & Constructors) (The Brain) (MVP) (**THIS IS THE CURRENT PHASE**)

**Goal**: Take user prompt and sucesfully pipe it through base agentic framework to make high quality input/output schemas.

1.  One by one, all core agents to the framework will be built and tested with unit testing of mostly inputs generated by me (or ai assisted). No agents' inputs/outputs will be linked at this stage yet.
2.  After core agents are built and tuned, these agents' inputs and outputs need to be linked to see how they function in a system. **This will be implemented using LangGraph**, which will define the state, nodes (agents), and conditional edges of the workflow.
3.  Tweak the individual agents' rules/principles and output structure to best align with each other to generate a high-quality end product. Agent relationships and rules will be provided in a JSON file. The cost of running these agents together should be calculated and considered/provided to me anytime designing.
4.  Analyze cost (API usage) of the current network of agents.
5.  Rinse and repeat the previous steps to get the highest quality outputs with a reasonable economic cost.

**Focus**: Simplicity. Use in-memory objects for storage; no vector DB yet. Vectorization will come when integrating the frontend and backend.

### Phase 2: Building writing and editing agents (Writers & Editors) (The Builders)

**Goal**: Build and add writing and editing agents to the network to take in Architect and Constructor schemas in order to start generating creative writing snippets.

1.  One by one, all generative agents to the framework will be built and tested with unit testing of input/output schemas from the Architect/Constructor agents.
2.  After all core agents are built and tuned, these agents' inputs and outputs need to be linked to each other to see how they function in a system.
3.  Tweak the individual agents' rules/principles and output structure to best align with each other to generate a high-quality end product. Agent relationships and rules will be provided in a JSON file. The cost of running these agents together should be calculated and considered/provided to me anytime designing.
4.  Analyze cost (API usage) of the current network of agents.
5.  Rinse and repeat the previous steps to get the highest quality outputs with a reasonable economic cost.

### Phase 3: Brain and Builder integration

**Goal**: Integrate the Brain and Builder agents together to be able to give a user prompt and have the agentic network produce a high-quality output (scope initially will be small for the amount of content we want outputted, this will be scaled up over time).

1.  **Using LangGraph**, start integrating Brain and Builder agents one by one and unit test outputs to make sure the integration is working well and what needs to be tweaked.
2.  Based on the quality of the integrated outputs, either tweak agents to better align with desired outputs or tweak the integration method depending on what seems to be the pain point.
3.  Rinse and repeat until outputs are a high-quality representation of user inputs.
4.  Consider the economic viability of agents and the various models they use.

### Phase 4: Refinement.. (Nothing here yet, more instructions will come when we are ready)

### Phase 5: Web Integration (Nothing here yet, more instructions will come with the MVP Python LangChain stage is fleshed out fully)

---

## Agent Invocation Framework: General Contractor vs. Subcontractors

This framework defines when to use the main, primary Claude session versus a specialized agent.

### The Main Session: The "General Contractor"

The main conversational session with Claude is the "General Contractor." It holds the full project context and is the default for all development tasks.

* **Primary Worker**: The main session should perform big picture changes to the repository.
* **Research Agents**: If research on a task is considered to be a good idea by Claude or the user explicitly states research needs to be done, you should check if one of the research agents is meant for this task; otherwise, let the main session do the research.
* **Developer Agents**: If there is a coding task that needs to be done, it should first be considered how much of the codebase this code change/addition/removal will impact. If the impact is large any touches many code files at once, the main session should probably do this coding task. If the impact is smaller in scope consider tasking a relevant developer agent. When the developer agent is done outputting, the main session should analyze agents output and either approve the change or raise concerns to the user if any problems are detected with what the agent wrote. At this point the user will tell the main agent to take over the task or have the agent try again maybe with extra added context.

* **When to Invoke a Developer Agent**: Below is a good framework for reasons to call upon agents:
    1.  **Repetitive & Boilerplate-Heavy**: Generating a new Pydantic model or a `pytest` file structure is an example of this.
    2.  **Low-Context & Rule-Based**: The task can be completed correctly without knowing the full project history.
    3.  **Requires High Precision**: The task demands a very specific format generally accepted by experts to not change much between many code files.