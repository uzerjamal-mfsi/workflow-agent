---
sidebar_position: 4
title: API Reference
description: Complete endpoint documentation for Workflow Agent REST API.
---

# API Reference

The Workflow Agent exposes REST API endpoints under `/` and `/api/v1`.

Interactive API documentation with live execution is available via Swagger UI at **`http://localhost:8000/docs`** and ReDoc at **`http://localhost:8000/redoc`**.

---

## Authentication

All `/api/v1/*` chat endpoints are secured via **API Key authentication**.

Requests must include the API key in the `X-API-Key` HTTP header:

```http
X-API-Key: <your-api-key>
```

- Configure your server key using the `API_KEY` (or `CHAT_API_KEY`) environment variable in `.env`. There is no default value; the variable must be set in the environment or `.env`, otherwise the application fails to start with a configuration validation error.
- The `/health` endpoint is public and does not require authentication.
- In **Swagger UI** (`/docs`), click the **Authorize** button (padlock icon) and enter your API key to test secured endpoints interactively.

### Authentication Error Responses

When authentication fails, endpoints return `401 Unauthorized`:

**Missing API Key (`401 Unauthorized`):**
```json
{
  "detail": "Missing API Key. Provide it in the 'X-API-Key' header."
}
```

**Invalid API Key (`401 Unauthorized`):**
```json
{
  "detail": "Invalid API Key."
}
```

---

## Endpoints

### 1. Health Check

#### `GET /health`
Returns the operational status of the service. This endpoint is public and requires no authentication.

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

**Headers:**

| Header | Type | Required | Description |
|---|---|---|---|
| `X-API-Key` | string | Yes | Secret API Key for authentication. |
| `Content-Type` | string | Yes | `application/json` |

**Request Body (`ChatRequest`):**

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | The natural language goal or command. |
| `thread_id` | string | No | Session identifier for persistence. Auto-generated UUID if omitted. |

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: workflow-agent-secret-key" \
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

**Response `401 Unauthorized`:**
```json
{
  "detail": "Missing API Key. Provide it in the 'X-API-Key' header."
}
```

---

### 3. Human-in-the-Loop Approval

#### `POST /api/v1/chat/approve`
Resumes a workflow thread paused at the `approval_gate`. Use this endpoint to grant approval or submit corrective feedback for replanning.

**Headers:**

| Header | Type | Required | Description |
|---|---|---|---|
| `X-API-Key` | string | Yes | Secret API Key for authentication. |
| `Content-Type` | string | Yes | `application/json` |

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
  -H "X-API-Key: workflow-agent-secret-key" \
  -d '{
    "thread_id": "thread-001",
    "approved": true
  }'
```

**Example 2 — Reject with Feedback (Triggers Re-planning):**
```bash
curl -X POST http://localhost:8000/api/v1/chat/approve \
  -H "Content-Type: application/json" \
  -H "X-API-Key: workflow-agent-secret-key" \
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

**Response `401 Unauthorized`:**
```json
{
  "detail": "Invalid API Key."
}
```
