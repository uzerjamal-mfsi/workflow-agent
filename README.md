# Workflow Agent

An autonomous workflow execution agent built with **FastAPI** and **LangGraph**. It translates natural language goals into structured execution plans, retrieves standard operating procedures (SOPs) via **Qdrant**, enforces security and dependency policies, integrates **Human-in-the-Loop** approval gates, and reliably executes actions with automatic verification and error recovery.

---

## Workflow Flow Diagram

The state machine manages the complete execution lifecycle with conditional routing for approvals, retries, and re-planning:

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
  [ generate_structured_plan ] ◀──────────────────┐ (Feedback provided)
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
      │   [ execute_next_tool ] ◀─────────┐       │
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

### Flow Conditions Summary

| Node | Decision / Condition | Destination |
|---|---|---|
| **approval_gate** | `approved == True` (or no approval required) | `execute_next_tool` |
| **approval_gate** | Human provided `feedback` | `generate_structured_plan` (replan) |
| **approval_gate** | Rejected without feedback or invalid plan | `END` |
| **verify** | Step succeeded, more steps remaining (`next_step`) | `execute_next_tool` |
| **verify** | Transient failure, retries < 3 (`retry`) | `execute_next_tool` |
| **verify** | Logical error detected (`replan`) | `generate_structured_plan` (replan) |
| **verify** | All steps complete (`completed`) or fatal error (`escalate`) | `END` |

---

## Features

- **Goal Parsing & Plan Generation**: Converts natural language requests into structured DAG action steps.
- **SOP Retrieval**: Semantically retrieves standard operating procedures from Qdrant vector store.
- **Policy & Permission Enforcement**: Identifies sensitive operations and bulk updates that require human sign-off.
- **Human-in-the-Loop Approval Gate**: Pauses execution using LangGraph interrupts until approved or replanned with user feedback.
- **Automated Verification & Recovery**: Verifies step output, retries transient network errors (up to 3x), and replans on logical parameter errors.
- **State Persistence**: Checkpoints execution state using PostgreSQL (or in-memory for testing).

---

## How to Run

### Prerequisites

- **Docker & Docker Compose** (recommended)
- Or for local runs: **Python 3.11+**, **[uv](https://docs.astral.sh/uv/)**, and an **OpenRouter API Key**

### 1. Configure Environment

Copy the `.env.example` file to `.env` and add your OpenRouter credentials:

```bash
cp .env.example .env
```

Set the essential variables:

```ini
OPENROUTER_API_KEY="your-openrouter-key"
MODEL_NAME="nvidia/nemotron-3-ultra-550b-a55b:free"
CHECKPOINTER_TYPE="memory"  # or "postgres"
API_KEY="secret-key"  # API key for /api/v1/
```

### 2. Start the Service

#### Option A: Docker Compose (Recommended)

Starts the API, PostgreSQL, and Qdrant containers all at once:

```bash
docker compose up --build
```

Run in the background:
```bash
docker compose up -d --build
```

#### Option B: Local Python Development

1. **Start backing databases (PostgreSQL & Qdrant):**
   ```bash
   docker compose up -d postgres qdrant
   ```

2. **Install dependencies and setup git hooks:**
   ```bash
   make setup
   # or: uv sync --extra dev && uv run pre-commit install
   ```

3. **Seed mock data & ingest SOP documentation:**
   ```bash
   make seed-db
   make ingest-sops
   ```

4. **Launch the FastAPI application:**
   ```bash
   uv run uvicorn app.main:app --reload
   ```

---

## How to Access

| Interface | URL | Description |
|---|---|---|
| **API Root** | `http://localhost:8000` | Application root |
| **Swagger UI** | `http://localhost:8000/docs` | Interactive OpenAPI playground |
| **ReDoc** | `http://localhost:8000/redoc` | API reference viewer |
| **Health Check** | `http://localhost:8000/health` | Liveness endpoint |
| **Documentation Site** | `http://localhost:3000` | Docusaurus docs (`make docs`) |

---

## Quick Usage Examples

### 1. Health Check

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### 2. Initiate a Workflow Goal

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secret-key" \
  -d '{
    "message": "Check calendar availability for user-1 on 2026-11-10",
    "thread_id": "session-101"
  }'
```

### 3. Approve a Sensitive Operation (Human-in-the-Loop)

When an operation requires approval (e.g. notifications or bulk updates), resume the thread:

```bash
curl -X POST http://localhost:8000/api/v1/chat/approve \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secret-key" \
  -d '{
    "thread_id": "session-101",
    "approved": true
  }'
```

Or provide corrective feedback to trigger automatic re-planning:

```bash
curl -X POST http://localhost:8000/api/v1/chat/approve \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secret-key" \
  -d '{
    "thread_id": "session-101",
    "approved": false,
    "feedback": "Change the priority to high and assign to user-2"
  }'
```

---

## Running Tests

Run the test suite:

```bash
# Locally
uv run pytest -q app/tests

# In Docker
docker compose run tests
```

---

## Documentation (Docusaurus)

```bash
# Start documentation site locally
make docs

# Build static production documentation site
make docs-build
```

---

## License

This project is licensed under the [MIT License](LICENSE.md).
