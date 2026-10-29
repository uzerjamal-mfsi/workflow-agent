import importlib
import os

from app.config import env_config


def test_reads_from_env(clear_env, set_env_vars):
    """Verify Settings loads values from environment."""
    importlib.reload(env_config)
    settings = env_config.Settings()

    assert settings.ENV == "dev"
    assert settings.PROJECT_NAME == "TestProj"
    assert settings.PROJECT_VERSION == "1.0.0"
    assert settings.ALLOWED_ORIGINS == ["http://localhost", "http://127.0.0.1"]
    assert settings.OPENROUTER_API_KEY == "or-test"
    assert (
        settings.DATABASE_URL
        == "postgresql+asyncpg://postgres:postgres@localhost:5432/workflow_agent_test"
    )
    assert settings.USE_QDRANT is True
    assert settings.QDRANT_URL == "http://qdrant:6333"


def test_paths_from_working_dir(clear_env, set_env_vars):
    """Verify paths are derived from WORKING_DIR."""
    importlib.reload(env_config)
    settings = env_config.Settings()

    expected_project_dir = os.path.join(str(set_env_vars), "TestProj")
    assert settings.WORKING_PROJECT_DIR == expected_project_dir
    assert settings.LOG_DIR == os.path.join(expected_project_dir, "logs")


def test_defaults_when_missing(clear_env, monkeypatch, tmp_path):
    # _env_file=None keeps the local .env out of the test; only os.environ is read.
    monkeypatch.setenv("PROJECT_NAME", "TestProj")
    monkeypatch.setenv("WORKING_DIR", str(tmp_path))
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/workflow_agent_test",
    )
    importlib.reload(env_config)
    settings = env_config.Settings(_env_file=None)

    assert settings.ENV == "dev"
    assert settings.OPENROUTER_API_KEY is None
    assert settings.USE_QDRANT is True
    assert settings.QDRANT_HOST == "qdrant"
    assert settings.QDRANT_URL == "http://qdrant:6333"


def test_qdrant_url_custom(clear_env, monkeypatch, tmp_path):
    """Verify explicit QDRANT_URL configuration."""
    monkeypatch.setenv("PROJECT_NAME", "TestProj")
    monkeypatch.setenv("WORKING_DIR", str(tmp_path))
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/workflow_agent_test",
    )
    monkeypatch.setenv("QDRANT_URL", "http://qdrant.custom:6333")
    importlib.reload(env_config)
    settings = env_config.Settings(_env_file=None)

    assert settings.QDRANT_URL == "http://qdrant.custom:6333"
