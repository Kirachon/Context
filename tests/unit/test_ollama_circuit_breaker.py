import asyncio
import types
import pytest
import sys

from src.ai_processing.ollama_client import OllamaClient
from src.config.settings import settings


class DummySession:
    def __init__(self, should_fail=True):
        self.should_fail = should_fail

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, url, json):
        return self

    def raise_for_status(self):
        if self.should_fail:
            raise RuntimeError("boom")

    async def json(self):
        return {"response": "ok"}


@pytest.mark.asyncio
async def test_circuit_opens_and_recovers(monkeypatch):
    # Configure aggressive circuit breaker
    monkeypatch.setattr(settings, "ollama_cb_enabled", True)
    monkeypatch.setattr(settings, "ollama_cb_threshold", 2)
    monkeypatch.setattr(settings, "ollama_cb_window_seconds", 60)
    monkeypatch.setattr(settings, "ollama_cb_cooldown_seconds", 0)
    monkeypatch.setattr(settings, "ollama_max_retries", 1)

    client = OllamaClient()

    # Patch aiohttp.ClientSession to fail first
    class AioHTTPMod:
        class ClientTimeout:
            def __init__(self, total):
                self.total = total
        class ClientSession:
            def __init__(self, timeout=None):
                self.timeout = timeout
            async def __aenter__(self):
                return DummySession(should_fail=True)
            async def __aexit__(self, exc_type, exc, tb):
                return False

    import src.ai_processing.ollama_client as oc
    monkeypatch.setattr(oc, "aiohttp", AioHTTPMod, raising=False)

    # Two failures to open the circuit
    with pytest.raises(RuntimeError):
        await client.generate_response("p1")
    with pytest.raises(RuntimeError):
        await client.generate_response("p2")

    # Now circuit should be open and short-circuit further calls
    with pytest.raises(RuntimeError):
        await client.generate_response("p3")

    # Patch ClientSession to succeed now and allow half-open trial
    class AioHTTPMod2:
        class ClientTimeout:
            def __init__(self, total):
                self.total = total
        class ClientSession:
            def __init__(self, timeout=None):
                self.timeout = timeout
            async def __aenter__(self):
                return DummySession(should_fail=False)
            async def __aexit__(self, exc_type, exc, tb):
                return False
    monkeypatch.setattr(oc, "aiohttp", AioHTTPMod2, raising=False)

    # After cooldown 0, next call allowed and should succeed, closing circuit
    resp = await client.generate_response("p4")
    assert resp == "ok"

