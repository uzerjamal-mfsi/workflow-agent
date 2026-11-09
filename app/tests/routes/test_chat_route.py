from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.agents.checkpointer import get_checkpointer
from app.config.env_config import get_settings
from app.main import app
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import MemorySaver


@pytest.fixture
def memory_checkpointer():
    return MemorySaver()


@pytest.fixture
def auth_headers():
    settings = get_settings()
    return {"X-API-Key": settings.API_KEY.get_secret_value()}


@pytest.mark.asyncio
async def test_chat_endpoint(memory_checkpointer, auth_headers):
    """Test successful chat request with valid API key."""
    app.dependency_overrides[get_checkpointer] = lambda: memory_checkpointer
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                headers=auth_headers,
                json={"message": "Test goal", "thread_id": "test-thread-123"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["thread_id"] == "test-thread-123"
            assert "answer" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_endpoint_missing_api_key(memory_checkpointer):
    """Test chat request fails with 401 when API key is missing."""
    app.dependency_overrides[get_checkpointer] = lambda: memory_checkpointer
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "Test goal", "thread_id": "test-thread-123"},
            )
            assert response.status_code == 401
            assert (
                response.json()["detail"]
                == "Missing API Key. Provide it in the 'X-API-Key' header."
            )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_endpoint_invalid_api_key(memory_checkpointer):
    """Test chat request fails with 401 when API key is invalid."""
    app.dependency_overrides[get_checkpointer] = lambda: memory_checkpointer
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                headers={"X-API-Key": "wrong-key"},
                json={"message": "Test goal", "thread_id": "test-thread-123"},
            )
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid API Key."
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_approve_endpoint(memory_checkpointer, auth_headers):
    """Test successful approval request with valid API key."""
    app.dependency_overrides[get_checkpointer] = lambda: memory_checkpointer
    try:
        with patch(
            "app.routes.core_routes.chat_route.get_workflow_graph"
        ) as mock_get_graph:
            mock_graph = MagicMock()
            mock_graph.ainvoke = AsyncMock(return_value={})
            mock_get_graph.return_value = mock_graph

            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/chat/approve",
                    headers=auth_headers,
                    json={
                        "thread_id": "test-thread-123",
                        "approved": True,
                        "feedback": "Approved by user",
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert data == {"status": "resumed", "thread_id": "test-thread-123"}
                mock_graph.ainvoke.assert_awaited_once()
                call_args = mock_graph.ainvoke.call_args
                command = call_args[0][0]
                assert command.resume == {
                    "approved": True,
                    "feedback": "Approved by user",
                }
                assert call_args[1]["config"] == {
                    "configurable": {"thread_id": "test-thread-123"}
                }
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_approve_endpoint_missing_api_key(memory_checkpointer):
    """Test approve request fails with 401 when API key is missing."""
    app.dependency_overrides[get_checkpointer] = lambda: memory_checkpointer
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/approve",
                json={
                    "thread_id": "test-thread-123",
                    "approved": True,
                },
            )
            assert response.status_code == 401
            assert (
                response.json()["detail"]
                == "Missing API Key. Provide it in the 'X-API-Key' header."
            )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_approve_endpoint_invalid_api_key(memory_checkpointer):
    """Test approve request fails with 401 when API key is invalid."""
    app.dependency_overrides[get_checkpointer] = lambda: memory_checkpointer
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/approve",
                headers={"X-API-Key": "wrong-key"},
                json={
                    "thread_id": "test-thread-123",
                    "approved": True,
                },
            )
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid API Key."
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_approve_endpoint_missing_approved(memory_checkpointer, auth_headers):
    """Test approve request returns 422 when approved field is missing."""
    app.dependency_overrides[get_checkpointer] = lambda: memory_checkpointer
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/approve",
                headers=auth_headers,
                json={"thread_id": "test-thread-123"},
            )
            assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_endpoint_unconfigured_server_key(memory_checkpointer):
    """Test server returns 500 if server-side API key is empty."""
    mock_settings = MagicMock()
    mock_settings.API_KEY.get_secret_value.return_value = ""
    app.dependency_overrides[get_checkpointer] = lambda: memory_checkpointer
    app.dependency_overrides[get_settings] = lambda: mock_settings
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                headers={"X-API-Key": "any-key"},
                json={"message": "Test goal", "thread_id": "test-thread-123"},
            )
            assert response.status_code == 500
            assert (
                response.json()["detail"] == "API Key is not configured on the server."
            )
    finally:
        app.dependency_overrides.clear()
