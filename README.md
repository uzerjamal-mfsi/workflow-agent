# Agentic Web Starter

<!-- Replace the URL below with your actual project logo/banner once available -->
![Agentic Web Starter](https://placehold.co/900x200?text=Agentic+Web+Starter)

FastAPI-based agentic RAG service with document ingestion and retrieval-augmented chat.

## Table of Contents

- [Agentic Web Starter](#agentic-web-starter)
  - [Table of Contents](#table-of-contents)
  - [Description](#description)
  - [Features](#features)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
  - [Usage](#usage)
    - [Interactive API docs](#interactive-api-docs)
    - [Quick examples](#quick-examples)
    - [Run tests](#run-tests)
    - [Documentation site](#documentation-site)
  - [Contributing](#contributing)
  - [License](#license)
  - [Acknowledgments](#acknowledgments)

---

## Description

**Agentic Web Starter** is a production-ready, batteries-included template for building agentic
RAG (Retrieval-Augmented Generation) web services with FastAPI.  It ships with:

- a vectorised document ingestion pipeline backed by **Qdrant**,
- a **chat endpoint** that retrieves relevant context before querying an LLM,
- **typed, validated settings** via `pydantic-settings`,
- optional **LangSmith tracing** wired into the chat model,
- a **Docusaurus** documentation site under `docs/` / `website/`, and
- CI via GitHub Actions running Ruff, mypy, pytest, gitleaks, and pip-audit on every push.

The starter is designed to be cloned and extended.  Add your own agents, prompts, or data
sources on top of the existing foundation.

---

## Features

- **Document ingestion** — File upload and indexing into Qdrant with configurable embedding
- **RAG chat** — Chat endpoint with retrieval augmentation and prompt orchestration
- **Validated configuration** — `pydantic-settings` model with defaults and startup validation
- **LLM tracing (optional)** — LangSmith tracer attached to the OpenRouter chat model
- **Global exception handling** — Consistent error responses (401, 403, 404, 422, 500)
- **Health check** — `/health` endpoint for liveness probes
- **Tests** — Pytest + pytest-asyncio suite runnable locally or via Docker Compose
- **CI pipeline** — GitHub Actions: Ruff, mypy, pytest, gitleaks, and pip-audit on every push
- **Documentation site** — Docusaurus handbook with setup, architecture, API, and contribution guides

---

## Getting Started

### Prerequisites

- **Python 3.11 or 3.12** for local development
- **[uv](https://docs.astral.sh/uv/)** for dependency management
- **Docker & Docker Compose** for containerised runs (recommended for production-like setups)
- **Qdrant** (included as a Docker Compose service)
- An **OpenRouter** API key for the LLM back-end

### Installation

1. **Clone the repository and enter the directory:**

   ```bash
   git clone https://github.com/<your-org>/agentic_web_starter.git
   cd agentic_web_starter
   ```

2. **Copy the environment template and fill in your values:**

   ```bash
   cp .env.example .env
   ```

   Key variables to configure:

   | Variable | Description |
   |----------|-------------|
   | `OPENROUTER_API_KEY` | Required for the chat endpoint |
   | `ALLOWED_ORIGINS` | Comma-separated CORS origins |
   | `USE_QDRANT` | Set `false` to disable Qdrant retrieval |
   | `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` | Optional LangSmith tracing |

   See `.env.example` and the [Configuration guide](docs/configuration.md) for the full list.

3. **Run with Docker Compose (recommended):**

   ```bash
   docker compose up --build
   ```

   The API is available at **http://localhost:8000**.

   *Or* bootstrap a local development environment:

   ```bash
   make setup                     # uv sync + registers all git hooks
   docker compose up -d qdrant    # start dependencies only
   uv run uvicorn app.main:app --reload
   ```

   `make setup` runs `uv sync --extra dev` and installs the pre-commit, commit-msg, and
   pre-push hooks. The pre-push hooks run mypy and pytest through `uv run`, so `uv` must be on
   `PATH` when you push.

---

## Usage

### Interactive API docs

Open **http://localhost:8000/docs** in your browser for Swagger UI.

### Quick examples

**Health check:**

```bash
curl http://localhost:8000/health
# {"message":"Up and running"}
```

**Chat with RAG:**

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "session-1", "query": "Summarise the document"}'
```

### Run tests

```bash
# In Docker (recommended — no local deps required)
docker compose run tests

# Locally (uv sync first)
uv run pytest -q app/tests
```

### Documentation site

```bash
make docs        # starts Docusaurus dev server at http://localhost:3000
make docs-build  # production build → website/build/
```

Refer to the [full documentation](docs/) for architecture decisions, configuration reference,
authentication flows, and the API reference.

---

## Contributing

Contributions are welcome!  Please read [CONTRIBUTING.md](docs/contributing.md) before opening a
pull request or issue.  The key points:

- Use [Conventional Commits](https://www.conventionalcommits.org/) for all commit messages.
  The `commit-msg` hook enforces this automatically after `make setup`.
- Run `pre-commit run --all-files` before pushing to ensure linting and formatting pass.
- All PRs must use the [pull request template](.github/pull_request_template.md) and reference a
  linked issue.
- Never push directly to `main`.

---

## License

This project is licensed under the **MIT License** — see [LICENSE.md](LICENSE.md) for details.

---

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) — the web framework powering the API
- [Qdrant](https://qdrant.tech/) — vector database for similarity search
- [LangChain](https://www.langchain.com/) — orchestration framework for LLM pipelines
- [Docusaurus](https://docusaurus.io/) — documentation site generator
- [pre-commit](https://pre-commit.com/) — multi-language pre-commit hook framework
- [commitizen](https://commitizen-tools.github.io/commitizen/) — Conventional Commits enforcement
