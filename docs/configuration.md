---
sidebar_position: 5
title: Configuration
description: Environment variables reference for Workflow Agent.
---

# Configuration

Workflow Agent is configured via environment variables and `.env`. Settings are validated at startup via `pydantic-settings` in `app/config/env_config.py`.

To get started:

```bash
cp .env.example .env
```

---

## Environment Variables

### 1. LLM Settings

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | *(Required)* | OpenRouter API Key used to authenticate with LLM models. |
| `MODEL_NAME` | *(Required)* | Target LLM model name (e.g. `openai/gpt-4o-mini`, `anthropic/claude-3.5-sonnet`). |

### 2. Qdrant (Vector Database)

| Variable | Default | Description |
|---|---|---|
| `QDRANT_URL` | `http://localhost:6333` | URL for Qdrant vector database instance. |
| `QDRANT_COLLECTION` | `workflow-sop` | Name of the collection storing SOP embeddings. |
| `QDRANT_API_KEY` | `None` | Optional API key for managed/remote Qdrant instances. |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Hugging Face embedding model used for vectorization. |
| `EMBEDDING_DIMENSION` | `384` | Dimension of vectors produced by the embedding model. |

### 3. PostgreSQL & Persistence

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/workflow_agent` | PostgreSQL connection string for mock tools and checkpoint storage. |
| `CHECKPOINTER_TYPE` | `memory` | State checkpointer engine. Choose `memory` for transient local runs or `postgres` for persistent multi-turn workflows. |

### 4. LangSmith Tracing (Optional)

| Variable | Default | Description |
|---|---|---|
| `LANGSMITH_TRACING` | `false` | Set to `true` to enable execution tracing in LangSmith. |
| `LANGSMITH_API_KEY` | `None` | LangSmith API Key (required if tracing is enabled). |
| `LANGSMITH_PROJECT` | `workflow-sop` | Target project name in LangSmith. |

### 5. Application Metadata & CORS

| Variable | Default | Description |
|---|---|---|
| `ENV` | `dev` | Current environment (`dev`, `prod`). |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:8000` | Comma-separated list of allowed CORS origins. |
| `WORKING_DIR` | *(Current directory)* | Working directory path for storage and caches. |
