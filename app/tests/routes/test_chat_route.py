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
