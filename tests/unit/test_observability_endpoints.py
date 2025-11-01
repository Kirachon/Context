from fastapi.testclient import TestClient
from src.mcp_server.server import app


def test_metrics_json_and_ready():
    client = TestClient(app)

    r = client.get("/metrics.json")
    assert r.status_code == 200
    data = r.json()
    assert "counters" in data and "histograms" in data

    r2 = client.get("/ready")
    assert r2.status_code == 200
    assert r2.json()["ready"] is True
