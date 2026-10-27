---
sidebar_position: 2
title: Getting started
description: Environment setup, Docker, and running the API locally.
---

# Getting started

This page walks you from a fresh clone to a running API. If you run into trouble, check the
[Configuration](./configuration) page for the full variable reference or open an issue.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Python 3.11 or 3.12** | See `pyproject.toml` for the supported range |
| **uv** | Installs dependencies and runs tooling |
| **Docker & Docker Compose** | Required for the recommended setup |
| **OpenRouter API key** | Needed for the chat endpoint |

---

## Step 1 — Configure your environment

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` in your editor. The most important variables to set right away are:

| Variable | Why it matters |
|----------|----------------|
| `OPENROUTER_API_KEY` | Powers the chat endpoint |
| `ALLOWED_ORIGINS` | Comma-separated origins allowed by CORS |
| `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` | Optional: send LLM traces to LangSmith |

See [Configuration](./configuration) for the full list.

**Never commit `.env` to version control.** It is already in `.gitignore`.

---

## Step 2 — Start the service

### Option A — Docker Compose (recommended)

This starts the API and Qdrant:

```bash
docker compose up --build
```

The API is available at **http://localhost:8000**.
Open **http://localhost:8000/docs** for interactive Swagger UI.

Other useful commands:

```bash
docker compose up -d --build   # run in the background (detached)
docker compose down            # stop all services
docker compose run tests       # run the test suite inside Docker
```

### Option B — Local Python with Docker for Qdrant

**1. Start the backing service:**

```bash
docker compose up -d qdrant
```

Point the API at the published port in `.env`:

```
QDRANT_HOST=localhost
```

**2. Bootstrap your Python environment (run once per clone):**

```bash
make setup
```

This runs `uv sync --extra dev` and registers the pre-commit, pre-push, and commit-msg hooks.

**Manual setup (without Make):**

```bash
uv sync --extra dev
uv run pre-commit install
```

**3. Start the API:**

```bash
uv run uvicorn app.main:app --reload
```

Or production-style with Gunicorn:

```bash
uv run gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## Step 3 — Verify everything is working

```bash
curl http://localhost:8000/health
# Expected: {"message":"Up and running"}
```

Then open **http://localhost:8000/docs** to explore the API interactively.

---

## Running tests

```bash
# Recommended — full stack inside Docker, no local deps required
docker compose run tests

# Locally
uv run pytest -q app/tests
```

---

## Next steps

- [Configuration](./configuration) — every environment variable and its default
- [Architecture](./architecture) — how the layers fit together
- [API reference](./api-reference) — endpoint list with request/response examples
