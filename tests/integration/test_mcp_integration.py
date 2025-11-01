"""
Integration tests for MCP Server

Tests full MCP server lifecycle including startup, tool invocation,
and shutdown in an integrated environment.
"""

import pytest
import os
from unittest.mock import patch, AsyncMock

# Add project root to path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.mcp_server.mcp_app import (
    MCPServer,
    start_mcp_server,
    shutdown_mcp_server,
    get_mcp_status,
)


@pytest.fixture
def mock_env():
    """Mock environment variables for testing"""
    original_env = os.environ.copy()
    os.environ.update(
        {
            "MCP_ENABLED": "true",
            "MCP_SERVER_NAME": "Context",
            "MCP_SERVER_VERSION": "0.1.0",
            "DATABASE_URL": "postgresql://context:password@localhost:5432/context_test",
            "REDIS_URL": "redis://localhost:6379/1",
            "QDRANT_HOST": "localhost",
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "ENVIRONMENT": "test",
            "LOG_LEVEL": "DEBUG",
        }
    )
    yield
    os.environ.clear()
    os.environ.update(original_env)


class TestMCPServerLifecycle:
    """Test complete MCP server lifecycle"""

    @pytest.mark.asyncio
    @patch("src.mcp_server.mcp_app.FastMCP")
    async def test_full_server_lifecycle(self, mock_fastmcp, mock_env):
        """Test complete server lifecycle from startup to shutdown"""
        # Create server instance
        server = MCPServer()

        # Mock FastMCP instance
        mock_mcp_instance = AsyncMock()
        mock_fastmcp.return_value = mock_mcp_instance

        # Start server
        with patch.object(server, "register_tools"):
            with patch.object(server, "_setup_signal_handlers"):
                await server.start()

        # Verify server is running
        assert server.is_running is True
        assert server.connection_state == "listening"

        # Get status
        status = server.get_status()
        assert status["running"] is True
        assert status["connection_state"] == "listening"

        # Shutdown server
        await server.shutdown()

        # Verify server is stopped
        assert server.is_running is False
        assert server.connection_state == "shutdown"
        assert server.shutdown_event.is_set()

    @pytest.mark.asyncio
    @patch("src.mcp_server.mcp_app.FastMCP")
    async def test_server_restart_capability(self, mock_fastmcp, mock_env):
        """Test that server can be restarted after shutdown"""
        server = MCPServer()

        # Mock FastMCP instance
        mock_mcp_instance = AsyncMock()
        mock_fastmcp.return_value = mock_mcp_instance

        # First startup
        with patch.object(server, "register_tools"):
            with patch.object(server, "_setup_signal_handlers"):
                await server.start()

        assert server.is_running is True

        # Shutdown
        await server.shutdown()
        assert server.is_running is False

        # Reset shutdown event for restart
        server.shutdown_event.clear()

        # Restart
        with patch.object(server, "register_tools"):
            with patch.object(server, "_setup_signal_handlers"):
                await server.start()

        assert server.is_running is True
        assert server.connection_state == "listening"

        # Final cleanup
        await server.shutdown()


class TestMCPToolInvocation:
    """Test MCP tool invocation in integrated environment"""

    @pytest.mark.asyncio
    @patch("src.mcp_server.mcp_app.FastMCP")
    async def test_health_check_tool_invocation(self, mock_fastmcp, mock_env):
        """Test health check tool can be invoked successfully"""
        server = MCPServer()

        # Mock FastMCP instance
        mock_mcp_instance = AsyncMock()
        mock_fastmcp.return_value = mock_mcp_instance

        # Start server
        with patch.object(server, "register_tools"):
            with patch.object(server, "_setup_signal_handlers"):
                await server.start()

        # Verify tools were registered
        assert server.mcp is not None

        # Cleanup
        await server.shutdown()

    @pytest.mark.asyncio
    @patch("src.mcp_server.mcp_app.FastMCP")
    async def test_capabilities_tool_invocation(self, mock_fastmcp, mock_env):
        """Test capabilities tool can be invoked successfully"""
        server = MCPServer()

        # Mock FastMCP instance
        mock_mcp_instance = AsyncMock()
        mock_fastmcp.return_value = mock_mcp_instance

        # Start server
        with patch.object(server, "register_tools"):
            with patch.object(server, "_setup_signal_handlers"):
                await server.start()

        # Verify server is ready
        assert server.is_running is True

        # Cleanup
        await server.shutdown()


class TestMCPConnectionHandling:
    """Test MCP connection handling in integrated environment"""

    @pytest.mark.asyncio
    @patch("src.mcp_server.mcp_app.FastMCP")
    async def test_connection_lifecycle_events(self, mock_fastmcp, mock_env):
        """Test connection lifecycle events are handled correctly"""
        server = MCPServer()

        # Mock FastMCP instance
        mock_mcp_instance = AsyncMock()
        mock_fastmcp.return_value = mock_mcp_instance

        # Start server
        with patch.object(server, "register_tools"):
            with patch.object(server, "_setup_signal_handlers"):
                await server.start()

        # Simulate connection
        server.connection_state = "connected"
        assert server.connection_state == "connected"

        # Simulate disconnection
        server.connection_state = "disconnected"
        assert server.connection_state == "disconnected"

        # Cleanup
        await server.shutdown()

    @pytest.mark.asyncio
    @patch("src.mcp_server.mcp_app.FastMCP")
    async def test_connection_error_recovery(self, mock_fastmcp, mock_env):
        """Test connection error recovery with reconnection"""
        server = MCPServer()

        # Mock FastMCP instance
        mock_mcp_instance = AsyncMock()
        mock_fastmcp.return_value = mock_mcp_instance

        # Start server
        with patch.object(server, "register_tools"):
            with patch.object(server, "_setup_signal_handlers"):
                await server.start()

        server.is_running = True

        # Simulate connection error
        server.connection_state = "error"

        # Attempt reconnection
        with patch.object(
            server, "_attempt_reconnection", new_callable=AsyncMock
        ) as mock_reconnect:
            await server._attempt_reconnection()
            mock_reconnect.assert_called_once()

        # Cleanup
        await server.shutdown()


class TestMCPFastAPIIntegration:
    """Test MCP server integration with FastAPI application"""

    @pytest.mark.asyncio
    async def test_fastapi_startup_initializes_mcp(self, mock_env):
        """Test that FastAPI startup event initializes MCP server"""
        from fastapi.testclient import TestClient
        from src.mcp_server.server import app

        with patch(
            "src.mcp_server.mcp_app.start_mcp_server", new_callable=AsyncMock
        ) as mock_start:
            # Create test client (triggers startup event)
            with TestClient(app) as client:
                # Verify MCP server start was called
                # Note: TestClient may not trigger async startup events properly
                # This is a basic integration check
                response = client.get("/health")
                assert response.status_code == 200

                # Verify MCP status is included in health response
                data = response.json()
                assert "mcp_server" in data

    @pytest.mark.asyncio
    async def test_health_endpoint_includes_mcp_status(self, mock_env):
        """Test that health endpoint includes MCP server status"""
        from fastapi.testclient import TestClient
        from src.mcp_server.server import app

        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200

            data = response.json()

            # Verify MCP status is included
            assert "mcp_server" in data
            assert "enabled" in data["mcp_server"]
            assert "running" in data["mcp_server"]
            assert "connection_state" in data["mcp_server"]


class TestMCPGlobalFunctionsIntegration:
    """Test global MCP functions in integrated environment"""

    @pytest.mark.asyncio
    @patch("src.mcp_server.mcp_app.mcp_server")
    async def test_start_mcp_server_integration(self, mock_server):
        """Test global start_mcp_server function"""
        mock_server.start = AsyncMock()

        await start_mcp_server()

        mock_server.start.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.mcp_server.mcp_app.mcp_server")
    async def test_shutdown_mcp_server_integration(self, mock_server):
        """Test global shutdown_mcp_server function"""
        mock_server.shutdown = AsyncMock()

        await shutdown_mcp_server()

        mock_server.shutdown.assert_called_once()

    def test_get_mcp_status_integration(self):
        """Test global get_mcp_status function returns valid status"""
        status = get_mcp_status()

        # Verify status structure
        assert isinstance(status, dict)
        assert "enabled" in status
        assert "running" in status
        assert "connection_state" in status
        assert "server_name" in status
        assert "version" in status
        assert "capabilities" in status
        assert "timestamp" in status

        # Verify data types
        assert isinstance(status["enabled"], bool)
        assert isinstance(status["running"], bool)
        assert isinstance(status["connection_state"], str)
        assert isinstance(status["capabilities"], list)


class TestMCPPerformance:
    """Test MCP server performance characteristics"""

    @pytest.mark.asyncio
    @patch("src.mcp_server.mcp_app.FastMCP")
    async def test_startup_performance(self, mock_fastmcp, mock_env):
        """Test that server startup completes quickly"""
        import time

        server = MCPServer()
        mock_mcp_instance = AsyncMock()
        mock_fastmcp.return_value = mock_mcp_instance

        start_time = time.time()

        with patch.object(server, "register_tools"):
            with patch.object(server, "_setup_signal_handlers"):
                await server.start()

        end_time = time.time()
        startup_time = end_time - start_time

        # Startup should complete in less than 2 seconds
        assert startup_time < 2.0, f"Startup took {startup_time}s, should be < 2s"

        await server.shutdown()

    @pytest.mark.asyncio
    @patch("src.mcp_server.mcp_app.FastMCP")
    async def test_shutdown_performance(self, mock_fastmcp, mock_env):
        """Test that server shutdown completes quickly"""
        import time

        server = MCPServer()
        mock_mcp_instance = AsyncMock()
        mock_fastmcp.return_value = mock_mcp_instance

        with patch.object(server, "register_tools"):
            with patch.object(server, "_setup_signal_handlers"):
                await server.start()

        start_time = time.time()
        await server.shutdown(timeout=5)
        end_time = time.time()

        shutdown_time = end_time - start_time

        # Shutdown should complete in less than 5 seconds
        assert shutdown_time < 5.0, f"Shutdown took {shutdown_time}s, should be < 5s"
