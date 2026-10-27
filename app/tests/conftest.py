"""Pytest fixtures for application tests."""

import importlib

import pytest
from fastapi.testclient import TestClient

ENV_VARS = [
    "ENV",
    "PROJECT_NAME",
    "PROJECT_VERSION",
    "PROJECT_DESCRIPTION",
    "ALLOWED_ORIGINS",
    "BASE_PATH",
    "OPENROUTER_API_KEY",
    "WORKING_DIR",
    "HF_HOME",
    "COLLECTION_NAME",
    "USE_QDRANT",
    "QDRANT_HOST",
    "QDRANT_PORT",
    "QDRANT_PROTOCOL",
]


@pytest.fixture
def clear_env(monkeypatch):
    """Remove standard env vars so tests start with clean state."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def set_env_vars(monkeypatch, tmp_path):
    """Set required env vars for test runs.

    Args:
        monkeypatch: Pytest monkeypatch.
        tmp_path: Temporary directory path.

    Returns:
        tmp_path for use by dependent fixtures.
    """
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setenv("PROJECT_NAME", "TestProj")
    monkeypatch.setenv("PROJECT_VERSION", "1.0.0")
    monkeypatch.setenv("PROJECT_DESCRIPTION", "Test project")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost,http://127.0.0.1")
    monkeypatch.setenv("BASE_PATH", "")

    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")

    monkeypatch.setenv("WORKING_DIR", str(tmp_path))

    monkeypatch.setenv("USE_QDRANT", "true")
    return tmp_path


@pytest.fixture
def client(clear_env, set_env_vars, monkeypatch):
    """Provide a TestClient for the FastAPI app."""
    from app.config import env_config, log_config

    importlib.reload(env_config)
    importlib.reload(log_config)

    from app import starter as starter_module

    app = starter_module.start_application()
    yield TestClient(app)
