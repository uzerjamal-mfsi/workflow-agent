---
sidebar_position: 4
title: API Reference
description: Complete endpoint documentation for Workflow Agent REST API.
---

# API Reference

The Workflow Agent exposes REST API endpoints under `/` and `/api/v1`.

Interactive API documentation with live execution is available via Swagger UI at **`http://localhost:8000/docs`** and ReDoc at **`http://localhost:8000/redoc`**.

---

## Endpoints

### 1. Health Check

#### `GET /health`
Returns the operational status of the service.

**Response `200 OK`:**
```json
{
  "status": "ok"
}
```

---

### 2. Initiate Workflow

#### `POST /api/v1/chat`
Submits a user request to the workflow agent. The agent parses the goal, retrieves SOPs, creates an execution plan, and begins executing steps (or pauses if human approval is needed).

**Request Body (`ChatRequest`):**

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | The natural language goal or command. |
| `thread_id` | string | No | Session identifier for persistence. Auto-generated UUID if omitted. |

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a task for user-1 to review the onboarding doc",
    "thread_id": "thread-001"
  }'
```

**Response `200 OK` (`ChatResponse`):**
```json
{
  "thread_id": "thread-001",
  "answer": "Test"
}
```

---

### 3. Human-in-the-Loop Approval

#### `POST /api/v1/chat/approve`
Resumes a workflow thread paused at the `approval_gate`. Use this endpoint to grant approval or submit corrective feedback for replanning.

**Request Body (`ApprovalRequest`):**

| Field | Type | Required | Description |
|---|---|---|---|
| `thread_id` | string | Yes | The thread identifier of the paused workflow. |
| `approved` | boolean | Yes | `true` to approve and execute steps; `false` to reject. |
| `feedback` | string | No | Corrective feedback if rejecting or requesting plan revision. |

**Example 1 — Approve Plan:**
```bash
curl -X POST http://localhost:8000/api/v1/chat/approve \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "thread-001",
    "approved": true
  }'
```

**Example 2 — Reject with Feedback (Triggers Re-planning):**
```bash
curl -X POST http://localhost:8000/api/v1/chat/approve \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "thread-001",
    "approved": false,
    "feedback": "Please reassign this task to user-2 instead."
  }'
```

**Response `200 OK`:**
```json
{
  "status": "resumed",
  "thread_id": "thread-001"
}
```
