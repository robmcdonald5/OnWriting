# CLAUDE.md

This file provides guidance to Claude when working on the AI Creative Writing Assistant. It outlines the project architecture, technology stack, and the development workflow.

## Project Overview

This project is an **AI Creative Writing Assistant** that uses a multi-department agentic framework (Architects, Constructors, Writers, Editors).

The development strategy is two-phased:
1.  **AI Core Prototyping (Python)**: The initial agentic logic will be rapidly developed and tested in Python to leverage its mature AI ecosystem.
2.  **Production Implementation (TypeScript)**: Once the core logic is validated, it will be ported to TypeScript to build a robust, scalable backend for the final SvelteKit application.

---

## Technology Stack

This project uses two distinct stacks for its two development phases.

### Phase 1: AI Core Prototyping

* **Language**: Python
* **Agent Framework**: **LangChain** (the Python library), (input output schema for agents will use Pydantic models)
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
│       ├── agents/         # Individual agent logic (e.g., lore_master.py)
│       ├── core/           # Core components (e.g., task_orchestrator.py)
│       ├── pipelines/      # Multi-agent chains and workflows
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
│   ├── agents/             # Unit tests for each agent
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

### Phase 1: Core Agentic Writing Pipeline (Architects & Constructors) (The Brain) (MVP)

**Goal**: Take user prompt and sucesfully pipe it through base agentic framework to make high quality input/output schemas.

1. One by one all core agents to the framework will be built and tested with unit testing of mostly inputs generated by me (or ai assisted). No agents inputs / outputs will be linked at this stage yet.
2. After core agents are built and tuned these agents inputs and outputs need to be linked to see how they function in a system.
3. Tweek the individual agents rules/principles and output structure to best align with each other to generate high quality end product. Agent relationships and rules will be provided in JSON file. Cost of running these agents together should be calculated and considered / provided to me anytime designing.
4. Analyze cost (API usage) of current network of agents.
5. Rince and repeat previous steps to get the highest quality outputs with a reasonable economic cost.

**Focus**: Simplicity. Use in-memory objects for storage; no vector DB yet, vectorization will come when integrating frontend and backend.

### Phase 2: Building writing and editing agents (Writers & Editors) (The Builders)

**Goal**: Build and add writing and editing agents to network to take in Architect and Consturctor schemas in order to start generating creative writing snippets.

1. One by one all generative agents to the framework will be built and tested with unit testing of input/output schemas from the Architect Constructor agents.
2. After all core agents are built and tuned these agents inputs and outputs need to be linked to each other to see how they function in a system.
3. Tweek the individual agents rules/principles and output structure to best align with each other to generate high quality end product. Agent relationships and rules will be provided in JSON file. Cost of running these agents together should be calculated and considered / provided to me anytime designing.
4. Analyze cost (API usage) of current network of agents.
5. Rince and repeat previous steps to get the highest quality outputs with a reasonable economic cost.

### Phase 3: Brain and Builder integration

**Goal**: Integrate the Brain and Builder agents together to be able to give a user prompt and have the agentic network produce a high quality output (scope initially will be small for the amount of content we want outputed, this will be scaled up over time).

1. Start integrating Brain and Builder agents one by one and unit test outputs to make sure integration is working well and what needs tweeked.
2. Based on the quality of the integrated outputs either tweak agents to better align with desired outputs or tweak integration method depending on what seems to be the pain point.
3. Rince repeat until outputs are high quality representation of user inputs.
4. Consider economic viability of agents and the various models they use.

### Phase 4: Refinement.. (Nothing here yet, more instructions will come when we are ready)

### Phase 5: Web Integration (Nothing here yet, more instructions will come with the MVP Python LangChain stage is fleshed out fully)