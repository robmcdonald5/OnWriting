# Backend CLAUDE.md

This file provides backend-specific guidance to Claude when working on the AI Creative Writing Assistant's Python backend. It contains instructions, conventions, and documentation specific to the backend implementation.

---

## Core Directive: Maintain This Document 📜

Similar to the root CLAUDE.md, this document must be kept up-to-date with backend-specific architectural decisions, workflows, and conventions. When making changes that affect backend structure, patterns, or agent implementations, consider if this document needs updating.

---

## Lang Agent Framework Map Documentation

### Overview

The `lang-agent-framework-map.json` file is the **single source of truth** for the agentic architecture of this creative writing system. It documents all agents, their relationships, inputs, outputs, and how they integrate within the LangChain/LangGraph ecosystem.

**Location**: `backend/lang-agent-framework-map.json`

### Critical Maintenance Requirement ⚠️

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

## Backend-Specific Conventions

*[This section will be expanded as backend development progresses with Python-specific patterns, LangChain conventions, testing strategies, etc.]*