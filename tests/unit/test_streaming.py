import pytest
import httpx
from httpx import ASGITransport
from contextlib import asynccontextmanager

from src.mcp_server.server import app


@pytest.mark.asyncio
async def test_prompt_generate_streaming_mode(monkeypatch):
    """Test /prompt/generate with stream=true returns SSE"""

    class FakeClient:
        async def generate_response_stream(self, prompt, model=None, context=None):
            yield "Hello"
            yield " "
            yield "world"

    import src.ai_processing.ollama_client as oc
    monkeypatch.setattr(oc, "get_ollama_client", lambda: FakeClient())

    @asynccontextmanager
    async def noop_lifespan(_):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", noop_lifespan, raising=False)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/prompt/generate",
            json={"prompt": "test", "stream": True},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"
        content = resp.text
        assert "data: Hello" in content
        assert "data: world" in content
        assert "data: [DONE]" in content


@pytest.mark.asyncio
async def test_prompt_chat_streaming_mode(monkeypatch):
    """Test /prompt/chat with stream=true returns SSE"""

    class FakeClient:
        async def generate_response_stream(self, prompt, model=None, context=None):
            yield "pong"

    import src.ai_processing.ollama_client as oc
    monkeypatch.setattr(oc, "get_ollama_client", lambda: FakeClient())

    @asynccontextmanager
    async def noop_lifespan(_):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", noop_lifespan, raising=False)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/prompt/chat",
            json={"messages": [{"role": "user", "content": "ping"}], "stream": True},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"
        content = resp.text
        assert "data: pong" in content
        assert "data: [DONE]" in content

