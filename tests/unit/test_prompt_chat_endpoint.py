import pytest
import httpx
from httpx import ASGITransport
from contextlib import asynccontextmanager

from src.mcp_server.server import app


@pytest.mark.asyncio
async def test_prompt_chat_endpoint_returns_message(monkeypatch):
    class FakeGen:
        async def generate(self, prompt: str, model: str | None = None, context=None):
            return "pong"

    import src.ai_processing.response_generator as rg
    monkeypatch.setattr(rg, "get_response_generator", lambda: FakeGen())

    @asynccontextmanager
    async def noop_lifespan(_):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", noop_lifespan, raising=False)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/prompt/chat",
            json={"messages": [{"role": "user", "content": "ping"}], "model": "mistral:7b-instruct"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["model"] == "mistral:7b-instruct"
        assert data["message"]["role"] == "assistant"
        assert data["message"]["content"] == "pong"

