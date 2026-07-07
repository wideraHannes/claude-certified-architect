# Claude Certified Architect

Study notes and hands-on code for the Claude Certified Architect curriculum.

Curriculum overview: <https://claudecertificationguide.com/>

## How to use this repo

For each chapter: read the guide, then work through the code in the matching folder. Files are numbered as "rings" — start at ring 1 and build up.

## Chapters

### 01 — Agentic Architecture & Orchestration

Topics:

- 1.1 Agentic Loops — [`01_Agentic-Architecture_&_Orchestration/01_agentic_loops/`](01_Agentic-Architecture_%26_Orchestration/01_agentic_loops/)
  - Docs: <https://platform.claude.com/docs/en/agents-and-tools/tool-use/build-a-tool-using-agent>
- 1.2 Multi-Agent Orchestration
- 1.3 Subagent Invocation and Context Passing
- 1.4 Workflow Enforcement and Handoff — [`01_Agentic-Architecture_&_Orchestration/04_workflow_enforcement_handoff/`](01_Agentic-Architecture_%26_Orchestration/04_workflow_enforcement_handoff/)
- 1.5 Agent SDK Hooks — [`01_Agentic-Architecture_&_Orchestration/05_agent_sdk_hooks/`](01_Agentic-Architecture_%26_Orchestration/05_agent_sdk_hooks/)
- 1.6 Task Decomposition Strategies — [`01_Agentic-Architecture_&_Orchestration/06_task_decomposition/`](01_Agentic-Architecture_%26_Orchestration/06_task_decomposition/)
- 1.7 Session State and Resumption — [`01_Agentic-Architecture_&_Orchestration/07_session_state_resumption/`](01_Agentic-Architecture_%26_Orchestration/07_session_state_resumption/)

### 02 — Tool Design & MCP Integration

Topics:

- 2.1 Tool Schema Design — [`02_Tool-Design_&_MCP-Integration/01_tool_schema_design/`](02_Tool-Design_%26_MCP-Integration/01_tool_schema_design/)

### 03 — Claude Code Configuration & Workflows

### 04 — Prompt Engineering & Structured Output

### 05 — Context Management & Reliability

## Setup

```bash
uv sync
cp .env.example .env  # add ANTHROPIC_API_KEY
uv run python 01_Agentic-Architecture_\&_Orchestration/01_agentic_loops/ring_1_single_tool.py
```
