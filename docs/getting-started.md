---
sidebar_position: 2
title: Getting Started
description: How to set up, run, and access Workflow Agent.
---

# Getting Started

Follow these steps to configure, run, and interact with the Workflow Agent.

---

## Prerequisites

- **Docker & Docker Compose** (recommended)
- Or for local runs:
  - **Python 3.11 or 3.12**
  - **[uv](https://docs.astral.sh/uv/)** package manager
  - An **OpenRouter API Key**

---

## 1. Configure Environment

Copy the example `.env` file and set your keys:

```bash
cp .env.example .env
```

At minimum, provide your OpenRouter API key, model, and application API key (no default; required for chat routes):

```ini
OPENROUTER_API_KEY="your-openrouter-api-key"
MODEL_NAME="openai/gpt-4o-mini"
CHECKPOINTER_TYPE="memory"  # or "postgres" for persistent checkpointing
API_KEY="your-secret-api-key"  # Required: no default; must be set in .env
```

---

## 2. Run the Application

### Option A: Docker Compose (Recommended)

Starts the API, PostgreSQL database, and Qdrant vector database in containers:

```bash
docker compose up --build
```

To run in detached (background) mode:

```bash
docker compose up -d --build
```

To stop containers:

```bash
docker compose down
```

---

### Option B: Local Development

1. **Start backing services (PostgreSQL & Qdrant):**

   ```bash
   docker compose up -d postgres qdrant
   ```

2. **Install dependencies:**

   ```bash
   make setup
   # or manually: uv sync --extra dev
   ```

3. **Initialize mock database and ingest SOPs into Qdrant:**

   ```bash
   make seed-db
   make ingest-sops
   ```

4. **Start the API server:**

   ```bash
   uv run uvicorn app.main:app --reload
   ```

---

## 3. How to Access

| Resource | URL | Description |
|---|---|---|
| **API Base** | `http://localhost:8000` | Root API host |
| **Interactive Docs (Swagger UI)** | `http://localhost:8000/docs` | Test endpoints interactively |
| **ReDoc** | `http://localhost:8000/redoc` | Alternative API reference |
| **Health Check** | `http://localhost:8000/health` | Service liveness probe |
| **Documentation Site** | `http://localhost:3000` | Run with `make docs` |

---

## 4. Quick Verification

Check the health status:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

Send a workflow goal:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: workflow-agent-secret-key" \
  -d '{"message": "Check calendar availability for user-1 on 2026-11-10", "thread_id": "test-session"}'
```

---

## 5. Running Tests

Run the full pytest suite:

```bash
# Locally
uv run pytest -q app/tests

# In Docker
docker compose run tests
```
