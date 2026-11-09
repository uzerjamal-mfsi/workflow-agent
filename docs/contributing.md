---
sidebar_position: 6
title: Contributing
description: Contribution guidelines, code standards, and testing procedures.
---

# Contributing

Contributions to Workflow Agent are welcome. Follow these straightforward guidelines to ensure consistent code quality and seamless reviews.

---

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/thiga-mindfire/workflow-agent.git
   cd workflow-agent
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   ```

3. **Install dependencies and git hooks:**
   ```bash
   make setup
   # or manually:
   # uv sync --extra dev
   # uv run pre-commit install
   ```

---

## Branch Naming & Commits

- **Branch Naming**:
  - `feat/<description>` — New features
  - `fix/<description>` — Bug fixes
  - `docs/<description>` — Documentation updates
  - `refactor/<description>` — Code refactoring
  - `test/<description>` — Test additions or updates

- **Conventional Commits**:
  Commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
  ```
  feat(agents): add fallback routing in verification node
  fix(routes): validate approval request payload
  docs(readme): add architecture flow diagram
  ```

---

## Code Quality & Testing

Before submitting a pull request, run code checks and tests:

1. **Linting and formatting:**
   ```bash
   uv run ruff check app/
   uv run ruff format app/
   ```

2. **Type checking:**
   ```bash
   uv run mypy app/
   ```

3. **Run test suite:**
   ```bash
   uv run pytest -q app/tests
   ```

---

## Pull Request Process

1. Create your feature branch from `main`.
2. Ensure all linting, typing, and tests pass.
3. Open a Pull Request describing your changes and link any related issues.
