from fastapi.testclient import TestClient

from src.mcp_server.server import app, settings


def test_api_key_auth_enforcement(monkeypatch):
    # Enable API key auth
    monkeypatch.setattr(settings, "api_auth_enabled", True)
    monkeypatch.setattr(settings, "api_auth_scheme", "api_key")
    monkeypatch.setattr(settings, "api_key", "secret")

    client = TestClient(app)

    # Without key -> 401
    r = client.get("/health")
    assert r.status_code == 401

    # With wrong key -> 401
    r = client.get("/health", headers={"x-api-key": "wrong"})
    assert r.status_code == 401

    # With correct key -> 200 and has correlation id header
    r = client.get(
        "/health",
        headers={"x-api-key": "secret", settings.correlation_id_header: "cid-123"},
    )
    assert r.status_code == 200
    assert settings.correlation_id_header in r.headers
