"""API Key authentication dependency for chat routes."""

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config.env_config import Settings, get_settings

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="API Key for accessing protected chat endpoints",
)


async def verify_api_key(
    api_key: Annotated[str | None, Security(api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    """Verify incoming API key from X-API-Key header against server settings."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key. Provide it in the 'X-API-Key' header.",
        )

    expected_key = settings.API_KEY.get_secret_value()
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API Key is not configured on the server.",
        )

    if not secrets.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key.",
        )

    return api_key

