from unittest.mock import MagicMock

import pytest
from fastapi import APIRouter, FastAPI, HTTPException, Security
from pydantic import SecretStr, ValidationError

from app.auth.api_key import verify_api_key
from app.config.env_config import Settings, get_settings


@pytest.fixture
def sample_settings():
    current = get_settings()
    return Settings(
        OPENROUTER_API_KEY=current.OPENROUTER_API_KEY,
        MODEL_NAME=current.MODEL_NAME,
        API_KEY=SecretStr("test-secret-key-456"),
    )


@pytest.mark.asyncio
async def test_verify_api_key_valid(sample_settings):
    """Directly test verify_api_key succeeds when keys match."""
    result = await verify_api_key(
        api_key="test-secret-key-456", settings=sample_settings
    )
    assert result == "test-secret-key-456"


@pytest.mark.asyncio
async def test_verify_api_key_missing(sample_settings):
    """Directly test verify_api_key raises 401 when key is missing or None."""
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(api_key=None, settings=sample_settings)
    assert exc_info.value.status_code == 401
    assert "Missing API Key" in exc_info.value.detail

    with pytest.raises(HTTPException) as exc_info_empty:
        await verify_api_key(api_key="", settings=sample_settings)
    assert exc_info_empty.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_api_key_invalid(sample_settings):
    """Directly test verify_api_key raises 401 when key is invalid."""
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(api_key="wrong-key", settings=sample_settings)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid API Key."


@pytest.mark.asyncio
async def test_verify_api_key_unconfigured_server():
    """Directly test verify_api_key raises 500 when server has empty API_KEY."""
    mock_settings = MagicMock()
    mock_settings.API_KEY.get_secret_value.return_value = ""
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(api_key="any-client-key", settings=mock_settings)
    assert exc_info.value.status_code == 500
    assert "not configured" in exc_info.value.detail


def test_settings_missing_api_key_raises_error():
    """Test that Settings raises ValidationError when API_KEY is not provided."""
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            OPENROUTER_API_KEY=SecretStr("test-key"),
            MODEL_NAME="test-model",
        )


def test_settings_empty_api_key_raises_error():
    """Test that Settings raises ValidationError when API_KEY is empty."""
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            OPENROUTER_API_KEY=SecretStr("test-key"),
            MODEL_NAME="test-model",
            API_KEY="",
        )


def test_auth_openapi_schema():
    """Test that OpenAPI schema includes APIKeyHeader security scheme."""
    app = FastAPI()
    router = APIRouter(dependencies=[Security(verify_api_key)])

    @router.get("/protected")
    def protected():
        return {"ok": True}

    app.include_router(router)
    schema = app.openapi()

    assert "components" in schema
    assert "securitySchemes" in schema["components"]
    assert "APIKeyHeader" in schema["components"]["securitySchemes"]
    assert (
        schema["components"]["securitySchemes"]["APIKeyHeader"]["name"] == "X-API-Key"
    )
    assert schema["components"]["securitySchemes"]["APIKeyHeader"]["in"] == "header"
    assert schema["paths"]["/protected"]["get"]["security"] == [{"APIKeyHeader": []}]


def test_settings_chat_api_key_alias():
    """Test that CHAT_API_KEY alias works in Settings."""
    current = get_settings()
    s = Settings(
        OPENROUTER_API_KEY=current.OPENROUTER_API_KEY,
        MODEL_NAME=current.MODEL_NAME,
        CHAT_API_KEY="custom-alias-key",
    )
    assert s.API_KEY.get_secret_value() == "custom-alias-key"
