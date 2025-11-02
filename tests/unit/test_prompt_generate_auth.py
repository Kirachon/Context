import pytest
import httpx
from httpx import ASGITransport
from contextlib import asynccontextmanager

from src.mcp_server.server import app


@pytest.mark.asyncio
async def test_prompt_generate_requires_api_key(monkeypatch):
    # Enable API key auth in server settings
    import src.mcp_server.server as srv
    srv.settings.api_auth_enabled = True
    srv.settings.api_auth_scheme = "api_key"
    srv.settings.api_key = "secret"

    # Patch generator to avoid external calls
    class FakeGen:
        async def generate(self, prompt: str, model: str | None = None, context=None):
            return "pong"

    import src.ai_processing.response_generator as rg
    monkeypatch.setattr(rg, "get_response_generator", lambda: FakeGen())

    # Disable lifespan for speed
    @asynccontextmanager
    async def noop_lifespan(_):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", noop_lifespan, raising=False)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Missing API key: should 401
        r1 = await client.post("/prompt/generate", json={"prompt": "ping"})
        assert r1.status_code == 401

        # Wrong API key: 401
        r2 = await client.post(
            "/prompt/generate",
            headers={"x-api-key": "wrong"},
            json={"prompt": "ping"},
        )
        assert r2.status_code == 401

        # Correct API key: 200
        r3 = await client.post(
            "/prompt/generate",
            headers={"x-api-key": "secret"},
            json={"prompt": "ping"},
        )
        assert r3.status_code == 200
        data = r3.json()
        assert data["success"] is True
        assert data["response"] == "pong"

