# Contributing to Workflow Agent

Contributions to Workflow Agent are welcome! Follow these guidelines to keep collaboration smooth and effective.

---

## Quick Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/thiga-mindfire/workflow-agent.git
   cd workflow-agent
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   ```

3. **Install dependencies and hooks:**
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
  - `docs/<description>` — Documentation changes
  - `refactor/<description>` — Refactoring
  - `test/<description>` — Tests

- **Commit Standards**:
  Follow [Conventional Commits](https://www.conventionalcommits.org/):
  ```
  feat(agents): add fallback routing in verification node
  fix(routes): validate approval request payload
  docs(readme): add workflow flow diagram
  ```

---

## Quality Checks & Testing

Always verify before committing:

```bash
# Lint and format
uv run ruff check app/
uv run ruff format app/

# Type checking
uv run mypy app/

# Run tests
uv run pytest -q app/tests
```

---

## Pull Request Process

1. Create a branch for your change.
2. Ensure linting, typing, and tests pass.
3. Open a Pull Request with a clear summary of what changed and why.
