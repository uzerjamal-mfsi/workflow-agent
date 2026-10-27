---
sidebar_position: 3
title: Configuration
description: Environment variables validated by app.config.env_config.Settings.
---

# Configuration

Settings are declared as a `pydantic-settings` model in `app/config/env_config.py`.
Values are read from the process environment first and then from `.env`, so environment
variables always win. Unknown variables are ignored; invalid values fail at startup.

To configure the project:

```bash
cp .env.example .env
# Edit .env with your values
```

**Never commit `.env`.** It is already in `.gitignore`; use `.env.example` for placeholders.

---

## Project and API

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV` | `dev` | Environment name. `dev` enables debug logging. |
| `PROJECT_NAME` | `agentic_web_starter` | FastAPI title, and the directory name under `WORKING_DIR`. |
| `PROJECT_VERSION` | `0.1.0` | Appears in the OpenAPI schema. |
| `PROJECT_DESCRIPTION` | `An agentic workflow automation application.` | Appears in the OpenAPI schema. |
| `ALLOWED_ORIGINS` | *(empty)* | Comma-separated CORS origins, e.g. `http://localhost:3000,https://myapp.com`. Empty entries are dropped. |
| `BASE_PATH` | *(empty)* | Root path when running behind a reverse proxy. Also shifts the OpenAPI URL. |

---

## Working directory

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKING_DIR` | `.` | Base directory for logs and the Hugging Face cache. |
| `HF_HOME` | `<WORKING_DIR>/<PROJECT_NAME>/hf` | Hugging Face cache. Exported to the process environment. |

Derived read-only settings (not set via env):

| Setting | Value |
|---------|-------|
| `WORKING_PROJECT_DIR` | `<WORKING_DIR>/<PROJECT_NAME>` |
| `LOG_DIR` | `<WORKING_DIR>/<PROJECT_NAME>/logs` |

---

## LLM

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | *(unset)* | Required for the `/api/v1/chat` endpoint. |

---

## Qdrant

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_QDRANT` | `true` | Enables the Qdrant-backed retrieval path. |
| `COLLECTION_NAME` | `agentic_web_starter` | Base name of the Qdrant collection. |
| `QDRANT_HOST` | `qdrant` | Hostname or IP (`localhost` when running outside Docker). |
| `QDRANT_PORT` | `6333` | HTTP port. |
| `QDRANT_PROTOCOL` | `http` | `http` or `https`. |

---

## LangSmith tracing

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGSMITH_TRACING` | `false` | Enables the LangSmith tracer attached to the chat model. |
| `LANGSMITH_API_KEY` | *(unset)* | Required when `LANGSMITH_TRACING=true`; startup fails otherwise. |
| `LANGSMITH_PROJECT` | `workflow-agent` | LangSmith project that receives the traces. |

---

## Full reference

- **`.env.example`** in the repository root — placeholders and comments
- **`app/config/env_config.py`** — typed fields, defaults, and validators
