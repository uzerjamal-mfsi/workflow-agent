from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.agents.checkpointer import get_checkpointer
from app.main import app
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import MemorySaver


@pytest.fixture
def memory_checkpointer():
    return MemorySaver()


@pytest.mark.asyncio
async def test_chat_endpoint(memory_checkpointer):
    app.dependency_overrides[get_checkpointer] = lambda: memory_checkpointer
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat",
                json={"message": "Test goal", "thread_id": "test-thread-123"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["thread_id"] == "test-thread-123"
            assert "answer" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_approve_endpoint(memory_checkpointer):
    app.dependency_overrides[get_checkpointer] = lambda: memory_checkpointer
    try:
        with patch("app.routes.core_routes.chat_route.get_workflow_graph") as mock_get_graph:
            mock_graph = MagicMock()
            mock_graph.ainvoke = AsyncMock(return_value={})
            mock_get_graph.return_value = mock_graph

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/chat/approve",
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
                assert command.resume == {"approved": True, "feedback": "Approved by user"}
                assert call_args[1]["config"] == {
                    "configurable": {"thread_id": "test-thread-123"}
                }
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_approve_endpoint_missing_approved(memory_checkpointer):
    app.dependency_overrides[get_checkpointer] = lambda: memory_checkpointer
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/approve",
                json={"thread_id": "test-thread-123"},
            )
            assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()

