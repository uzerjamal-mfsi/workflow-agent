---
sidebar_position: 3
title: Architecture
description: LangGraph state machine, nodes, conditional edges, and execution flow.
---

# Architecture

Workflow Agent is orchestrated as a stateful graph using **LangGraph**. Requests are processed through a directed acyclic state graph with conditional branches for Human-in-the-Loop approvals, tool verification, retry loops, and automatic re-planning.

---

## Workflow State Graph

The diagram below illustrates the complete graph flow, including all conditional branches and decision points:

```text
  [ START ]
      │
      ▼
  [ parse_goal ]
      │
      ▼
  [ retrieve_sops ]
      │
      ▼
  [ generate_structured_plan ] ◀───────────────────┐ (Feedback provided)
      │                                            │
      ▼                                            │ (Logical error replan)
  [ validate_dependencies_and_permissions ]        │
      │                                            │
      ▼                                            │
  [ approval_gate ] ───(Feedback provided)─────────┤
      │                                            │
      ├─► Approved / No Approval Needed            │
      │        │                                   │
      │        ▼                                   │
      │   [ execute_next_tool ] ◀──────────┐       │
      │        │                           │       │
      │        ▼                           │       │
      │   [ verify ]                       │       │
      │        │                           │       │
      │        ├─► Next Step / Retry ──────┘       │
      │        │                                   │
      │        ├─► Logical Error ──────────────────┘
      │        │
      │        └─► Completed / Escalate ───► [ END ]
      │
      └─► Rejected / Invalid ──────────────► [ END ]
```

---

## Graph Nodes & Responsibilities

| Node | Purpose | Behavior |
|---|---|---|
| `parse_goal` | Ingests the incoming request | Extracts the user's intent and populates `goal` in workflow state. |
| `retrieve_sops` | Context retrieval | Queries the **Qdrant** vector store for Standard Operating Procedures matching the goal. |
| `generate_structured_plan` | Plan creation | Uses the LLM to generate an ordered list of tool execution steps (`Plan`). |
| `validate_dependencies_and_permissions` | DAG & policy check | Validates dependency order, checks for cycles, and marks `requires_approval = True` if sensitive tools or bulk actions are present. |
| `approval_gate` | Human-in-the-Loop | If `requires_approval` is `False`, automatically approves. If `True`, triggers a LangGraph `interrupt()` and awaits human decision via `/api/v1/chat/approve`. |
| `execute_next_tool` | Tool execution | Executes the current step tool (e.g. `create_task`, `update_task`, `send_notification`, `check_calendar_availability`) and records `StepResult`. |
| `verify` | Result verification | Checks if the step succeeded. Increments retry counter for transient errors, flags logical errors for re-planning, or advances step index. |

---

## Conditional Routing Logic

### 1. `route_after_approval` (from `approval_gate`)

- **`execute_next_tool`**: State `approved == True` (either no approval required, or human confirmed approval).
- **`generate_structured_plan`**: Human provided feedback without approving (`feedback` is present), prompting the planner to revise the plan.
- **`END`**: Human rejected the request without feedback or plan validation failed.

### 2. `route_after_verification` (from `verify`)

- **`execute_next_tool`**:
  - `verification_outcome == "next_step"`: Step succeeded, moves to the next step in the plan.
  - `verification_outcome == "retry"`: Step encountered a transient failure (e.g. network timeout) and retry count < 3.
- **`generate_structured_plan`**: `verification_outcome == "replan"`: A logical error occurred (e.g. invalid parameter), triggering automatic re-planning with error context.
- **`END`**:
  - `verification_outcome == "completed"`: All plan steps finished successfully.
  - `verification_outcome == "escalate"`: Fatal error or max retries exceeded.

---

## State & Checkpointing

Workflow state is tracked via the `WorkflowState` schema:
- `thread_id`: Unique identifier for the workflow session.
- `goal`: Parsed user objective.
- `retrieved_sops`: SOP context retrieved from Qdrant.
- `plan`: Structured plan containing steps, tool names, and arguments.
- `current_step_index`: Pointer to the active step.
- `requires_approval`, `approved`, `feedback`: Human-in-the-Loop state.
- `completed_steps`: Results of successfully executed steps.
- `retry_count`: Transient retry counter.

State persistence is configured via `CHECKPOINTER_TYPE`:
- **`memory`**: Uses `MemorySaver` (in-memory, ideal for local tests).
- **`postgres`**: Uses `AsyncPostgresSaver` backed by PostgreSQL for production persistence.
