import pytest
import httpx
from httpx import ASGITransport

from src.mcp_server.server import app
from contextlib import asynccontextmanager


@pytest.mark.asyncio
async def test_prompt_generate_endpoint_returns_text(monkeypatch):
    class FakeGen:
        async def generate(self, prompt: str, model: str | None = None, context=None):
            return "pong"

    # Patch the response generator to avoid real Ollama calls
    import src.ai_processing.response_generator as rg

    monkeypatch.setattr(rg, "get_response_generator", lambda: FakeGen())

    # Disable app lifespan during the test to avoid heavy startup
    @asynccontextmanager
    async def noop_lifespan(_):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", noop_lifespan, raising=False)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/prompt/generate",
            json={"prompt": "ping", "model": "mistral:7b-instruct"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["response"] == "pong"
        assert data["model"] == "mistral:7b-instruct"

