import pytest
import httpx
from httpx import ASGITransport
from contextlib import asynccontextmanager

from src.mcp_server.server import app


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_threshold(monkeypatch):
    # Configure rate limit: 2 requests/minute keyed by IP
    import src.mcp_server.server as srv
    srv.settings.rate_limit_enabled = True
    srv.settings.rate_limit_key = "ip"
    srv.settings.rate_limit_requests_per_minute = 2

    class FakeGen:
        async def generate(self, prompt: str, model: str | None = None, context=None):
            return "ok"

    import src.ai_processing.response_generator as rg
    monkeypatch.setattr(rg, "get_response_generator", lambda: FakeGen())

    @asynccontextmanager
    async def noop_lifespan(_):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", noop_lifespan, raising=False)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # First two should pass
        r1 = await client.post("/prompt/generate", json={"prompt": "p1"})
        r2 = await client.post("/prompt/generate", json={"prompt": "p2"})
        assert r1.status_code == 200
        assert r2.status_code == 200

        # Third within same minute should be 429
        r3 = await client.post("/prompt/generate", json={"prompt": "p3"})
        assert r3.status_code == 429
        data = r3.json()
        assert data["error"] == "rate_limited"

