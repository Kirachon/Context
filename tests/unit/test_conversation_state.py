import pytest
import httpx
from httpx import ASGITransport
from contextlib import asynccontextmanager

from src.mcp_server.server import app


@pytest.mark.asyncio
async def test_chat_with_conversation_id_maintains_state(monkeypatch):
    """Test that conversation_id enables stateful multi-turn chat."""

    class FakeClient:
        async def generate_response(self, prompt, model=None, context=None, stream=False):
            # Echo back the prompt to verify history is included
            return f"Echo: {prompt}"

    import src.ai_processing.ollama_client as oc
    monkeypatch.setattr(oc, "get_ollama_client", lambda: FakeClient())

    @asynccontextmanager
    async def noop_lifespan(_):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", noop_lifespan, raising=False)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # First turn
        r1 = await client.post(
            "/prompt/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "conversation_id": "test-conv-123",
            },
        )
        assert r1.status_code == 200
        data1 = r1.json()
        assert data1["success"] is True
        assert "Hello" in data1["message"]["content"]

        # Second turn - should include history
        r2 = await client.post(
            "/prompt/chat",
            json={
                "messages": [{"role": "user", "content": "How are you?"}],
                "conversation_id": "test-conv-123",
            },
        )
        assert r2.status_code == 200
        data2 = r2.json()
        # The prompt should now include both the first user message and the assistant response
        assert "Hello" in data2["message"]["content"]
        assert "How are you?" in data2["message"]["content"]


@pytest.mark.asyncio
async def test_chat_without_conversation_id_is_stateless(monkeypatch):
    """Test that without conversation_id, chat is stateless."""

    class FakeClient:
        async def generate_response(self, prompt, model=None, context=None, stream=False):
            return f"Echo: {prompt}"

    import src.ai_processing.ollama_client as oc
    monkeypatch.setattr(oc, "get_ollama_client", lambda: FakeClient())

    @asynccontextmanager
    async def noop_lifespan(_):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", noop_lifespan, raising=False)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post(
            "/prompt/chat",
            json={"messages": [{"role": "user", "content": "First"}]},
        )
        assert r1.status_code == 200

        r2 = await client.post(
            "/prompt/chat",
            json={"messages": [{"role": "user", "content": "Second"}]},
        )
        assert r2.status_code == 200
        data2 = r2.json()
        # Should NOT include "First" since no conversation_id
        assert "First" not in data2["message"]["content"]
        assert "Second" in data2["message"]["content"]


@pytest.mark.asyncio
async def test_delete_conversation(monkeypatch):
    """Test DELETE /conversations/{id} endpoint."""

    @asynccontextmanager
    async def noop_lifespan(_):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", noop_lifespan, raising=False)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a conversation by chatting
        class FakeClient:
            async def generate_response(self, prompt, model=None, context=None, stream=False):
                return "ok"

        import src.ai_processing.ollama_client as oc
        monkeypatch.setattr(oc, "get_ollama_client", lambda: FakeClient())

        await client.post(
            "/prompt/chat",
            json={
                "messages": [{"role": "user", "content": "Hi"}],
                "conversation_id": "delete-test",
            },
        )

        # Delete it
        r = await client.delete("/conversations/delete-test")
        assert r.status_code == 204

        # Delete again should 404
        r2 = await client.delete("/conversations/delete-test")
        assert r2.status_code == 404


@pytest.mark.asyncio
async def test_conversation_stats(monkeypatch):
    """Test GET /conversations/stats endpoint."""

    @asynccontextmanager
    async def noop_lifespan(_):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", noop_lifespan, raising=False)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/conversations/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["enabled"] is True
        assert "total_conversations" in data
        assert "total_messages" in data

