"""Pytest fixtures for application tests."""

import importlib
import os

import pytest
from fastapi.testclient import TestClient

from app.services.jira_service import DEFAULT_TASKS

# Settings require DATABASE_URL at import time; tests do not connect to it.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/workflow_agent_test",
)

ENV_VARS = [
    "ENV",
    "PROJECT_NAME",
    "PROJECT_VERSION",
    "PROJECT_DESCRIPTION",
    "ALLOWED_ORIGINS",
    "BASE_PATH",
    "OPENROUTER_API_KEY",
    "WORKING_DIR",
    "DATABASE_URL",
    "HF_HOME",
    "COLLECTION_NAME",
    "USE_QDRANT",
    "QDRANT_HOST",
    "QDRANT_PORT",
    "QDRANT_PROTOCOL",
    "LANGSMITH_TRACING",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
]


@pytest.fixture(autouse=True)
def preserve_sample_tasks():
    """Ensure sample tasks.json remains unmodified across tests."""
    original = (
        DEFAULT_TASKS.read_text(encoding="utf-8") if DEFAULT_TASKS.exists() else None
    )
    yield
    if original is not None and DEFAULT_TASKS.exists():
        if DEFAULT_TASKS.read_text(encoding="utf-8") != original:
            DEFAULT_TASKS.write_text(original, encoding="utf-8")


@pytest.fixture
def clear_env(monkeypatch):
    """Remove standard env vars so tests start with clean state."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def set_env_vars(monkeypatch, tmp_path):
    """Set required env vars for test runs."""
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setenv("PROJECT_NAME", "TestProj")
    monkeypatch.setenv("PROJECT_VERSION", "1.0.0")
    monkeypatch.setenv("PROJECT_DESCRIPTION", "Test project")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost,http://127.0.0.1")
    monkeypatch.setenv("BASE_PATH", "")

    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")

    monkeypatch.setenv("WORKING_DIR", str(tmp_path))

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/workflow_agent_test",
    )

    monkeypatch.setenv("USE_QDRANT", "true")

    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    return tmp_path


@pytest.fixture
def app(clear_env, set_env_vars):
    """Provide a freshly configured FastAPI app."""
    from app.config import env_config, log_config

    importlib.reload(env_config)
    importlib.reload(log_config)

    from app import starter as starter_module

    return starter_module.start_application()


@pytest.fixture
def client(app):
    """Provide a TestClient for the FastAPI app."""
    yield TestClient(app)
