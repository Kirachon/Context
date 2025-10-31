"""
Unit tests for Context MCP Server

Tests the FastAPI application including health check endpoints
and basic server functionality.
"""

import pytest
from fastapi.testclient import TestClient
from src.mcp_server.server import app
import os


@pytest.fixture
def client():
    """Create a test client for the FastAPI application"""
    return TestClient(app)


@pytest.fixture
def mock_env():
    """Mock environment variables for testing"""
    original_env = os.environ.copy()
    os.environ.update({
        "DATABASE_URL": "postgresql://context:password@localhost:5432/context_test",
        "REDIS_URL": "redis://localhost:6379/1",
        "QDRANT_HOST": "localhost",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "ENVIRONMENT": "test"
    })
    yield
    os.environ.clear()
    os.environ.update(original_env)


def test_root_endpoint(client):
    """Test the root endpoint returns basic server information"""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Context"
    assert data["version"] == "0.1.0"
    assert data["description"] == "100% Offline AI Coding Assistant"
    assert data["status"] == "running"
    assert data["health_endpoint"] == "/health"
    assert data["docs_endpoint"] == "/docs"


def test_health_endpoint_structure(client, mock_env):
    """Test the health endpoint returns properly structured response"""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "status" in data
    assert "version" in data
    assert "timestamp" in data
    assert "environment" in data
    assert "services" in data
    assert "mcp_server" in data

    # Verify status is either healthy or degraded
    assert data["status"] in ["healthy", "degraded"]

    # Verify version
    assert data["version"] == "0.1.0"

    # Verify environment
    assert data["environment"] == "test"

    # Verify services dict structure
    services = data["services"]
    assert isinstance(services, dict)
    assert "postgres" in services
    assert "redis" in services
    assert "qdrant" in services
    assert "ollama" in services

    # Verify MCP server status structure
    mcp_server = data["mcp_server"]
    assert isinstance(mcp_server, dict)
    assert "enabled" in mcp_server
    assert "running" in mcp_server
    assert "connection_state" in mcp_server


def test_health_endpoint_services_status(client, mock_env):
    """Test that health endpoint checks all required services"""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    services = data["services"]

    # Each service should have a boolean status
    for service_name, status in services.items():
        assert isinstance(status, bool), f"Service {service_name} status should be boolean"


def test_health_endpoint_healthy_status(client, mock_env):
    """Test that overall status is healthy when all services are available"""
    response = client.get("/health")
    data = response.json()

    # If all services are True, status should be healthy
    if all(data["services"].values()):
        assert data["status"] == "healthy"


def test_health_endpoint_degraded_status(client):
    """Test that overall status is degraded when services are unavailable"""
    # Clear environment variables to simulate unavailable services
    original_env = os.environ.copy()
    os.environ.clear()

    response = client.get("/health")
    data = response.json()

    # When services are unavailable, status should be degraded
    if not all(data["services"].values()):
        assert data["status"] == "degraded"

    # Restore environment
    os.environ.update(original_env)


def test_health_endpoint_timestamp_format(client, mock_env):
    """Test that health endpoint returns properly formatted ISO timestamp"""
    response = client.get("/health")
    data = response.json()

    timestamp = data["timestamp"]

    # Verify timestamp is ISO format string
    assert isinstance(timestamp, str)
    assert "T" in timestamp  # ISO format includes 'T' separator

    # Verify timestamp can be parsed (basic validation)
    from datetime import datetime
    parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    assert isinstance(parsed_timestamp, datetime)


def test_api_docs_available(client):
    """Test that API documentation endpoints are accessible"""
    # Test Swagger UI endpoint
    swagger_response = client.get("/docs")
    assert swagger_response.status_code == 200

    # Test ReDoc endpoint
    redoc_response = client.get("/redoc")
    assert redoc_response.status_code == 200


def test_openapi_schema_available(client):
    """Test that OpenAPI schema is available"""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert schema["info"]["title"] == "Context"
    assert schema["info"]["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_check_services_function(mock_env):
    """Test the check_services helper function"""
    from src.mcp_server.server import check_services

    services = await check_services()

    # Verify all required services are checked
    assert "postgres" in services
    assert "redis" in services
    assert "qdrant" in services
    assert "ollama" in services

    # Verify each service returns boolean status
    for service_name, status in services.items():
        assert isinstance(status, bool)


def test_health_endpoint_performance(client, mock_env):
    """Test that health endpoint responds quickly"""
    import time

    start_time = time.time()
    response = client.get("/health")
    end_time = time.time()

    # Health check should respond in less than 1 second
    response_time = end_time - start_time
    assert response_time < 1.0, f"Health check took {response_time}s, should be < 1s"
    assert response.status_code == 200
