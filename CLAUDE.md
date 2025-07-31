# CLAUDE.md

This file provides guidance to Claude when working on the AI Creative Writing Assistant. The immediate focus is on building and testing the agentic framework in the `backend/` directory.

## Project Overview

This project is an **AI Creative Writing Assistant** that uses a multi-agent framework to help users write stories. The core of the application is the `backend/`, which will house the agentic logic built with LangChain. The `frontend/` will be developed later with SvelteKit.

## Backend Technology Stack

* **Language**: TypeScript
* **Runtime**: Node.js
* **Package Manager**: `npm`
* **Agent Framework**: **LangChain.js** (e.g., `@langchain/core`, `@langchain/openai`, etc.)
* **Testing Framework**: **Vitest** for unit and integration testing.
* **Execution**: `ts` for running TypeScript files directly during development.

## Backend Directory Structure

When working in the `backend/` directory, please adhere to this structure

## Frontend Directory Structure

When working in the `frontend/` directory, please adhere to this structure

## Agent Development Workflow

The primary development loop should be **test-driven** and focused on individual agents before building the full API.

1.  **Focus**: All initial work should be within the `backend/` directory.
2.  **Define Logic**: For a new agent (e.g., `LoreMaster`), create a file at `src/agents/loreMaster.ts`. This file will contain the function(s) that encapsulate the agent's logic, including its LangChain chain definition.
3.  **Write a Test First**: Before implementing the agent fully, create a corresponding test file at `tests/agents/loreMaster.test.ts`. Write a unit test using **Vitest** that defines what the agent should do. For example, test that it accepts a genre and returns a structured lore object.
4.  **Implement the Agent**: Write the agent's logic in `src/agents/loreMaster.ts` to make the test pass. This involves creating prompt templates, defining the model, and building the chain.
5.  **Iterate**: Continue this "define -> test -> implement" cycle for each agent and chain.

## Key Commands

* **Run all tests**: `pnpm test`
* **Run a specific test file**: `pnpm test tests/agents/loreMaster.test.ts`
* **Run a script**: `pnpm dev src/some-script.ts`