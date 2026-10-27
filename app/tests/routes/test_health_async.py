from httpx import ASGITransport, AsyncClient


async def test_health_async(app):
    """Verify /health is served through the async ASGI stack."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"message": "Up and running"}
