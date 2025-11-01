"""
Unit tests for MCP Tools

Tests health check and capabilities tool endpoints.
"""

import pytest
import os
from unittest.mock import Mock, patch

# Add project root to path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.mcp_server.tools.health import register_health_tools, _check_services
from src.mcp_server.tools.capabilities import register_capability_tools
from src.config.settings import settings


@pytest.fixture
def mock_mcp():
    """Create a mock FastMCP instance"""
    mcp = Mock()
    mcp.tool = Mock(
        return_value=lambda f: f
    )  # Decorator that returns function unchanged
    return mcp


@pytest.fixture
def mock_env():
    """Mock environment variables for testing"""
    original_env = os.environ.copy()
    os.environ.update(
        {
            "DATABASE_URL": "postgresql://context:password@localhost:5432/context_test",
            "REDIS_URL": "redis://localhost:6379/1",
            "QDRANT_HOST": "localhost",
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "ENVIRONMENT": "test",
        }
    )
    yield
    os.environ.clear()
    os.environ.update(original_env)


class TestHealthTools:
    """Test health check tool endpoints"""

    def test_register_health_tools(self, mock_mcp):
        """Test that health tools are registered successfully"""
        register_health_tools(mock_mcp)

        # Verify tool decorator was called
        assert mock_mcp.tool.called

    @pytest.mark.asyncio
    async def test_check_services_function(self, mock_env):
        """Test the _check_services helper function"""
        services = await _check_services()

        # Verify all required services are checked
        assert "postgres" in services
        assert "redis" in services
        assert "qdrant" in services
        assert "ollama" in services

        # Verify each service returns boolean status
        for service_name, status in services.items():
            assert isinstance(status, bool)

    @pytest.mark.asyncio
    async def test_check_services_with_valid_config(self, mock_env):
        """Test service checks with valid configuration"""
        services = await _check_services()

        # With mock env, all services should be detected as configured
        assert services["postgres"] is True
        assert services["redis"] is True
        assert services["qdrant"] is True
        assert services["ollama"] is True

    @pytest.mark.asyncio
    async def test_check_services_with_missing_config(self):
        """Test service checks with missing configuration"""
        # Clear environment variables
        original_env = os.environ.copy()
        os.environ.clear()

        services = await _check_services()

        # Without env vars, services should be detected as unavailable
        assert services["postgres"] is False
        assert services["redis"] is False
        assert services["qdrant"] is False
        assert services["ollama"] is False

        # Restore environment
        os.environ.update(original_env)

    @pytest.mark.asyncio
    @patch("src.mcp_server.tools.health._check_services")
    @patch("src.mcp_server.mcp_app.get_mcp_status")
    async def test_health_check_tool_success(
        self, mock_mcp_status, mock_check_services
    ):
        """Test health_check tool returns correct structure"""
        # Setup mocks
        mock_check_services.return_value = {
            "postgres": True,
            "redis": True,
            "qdrant": True,
            "ollama": True,
        }
        mock_mcp_status.return_value = {
            "enabled": True,
            "running": True,
            "connection_state": "connected",
        }

        # Import and call the tool function directly
        from src.mcp_server.tools.health import register_health_tools

        # Create a mock MCP and register tools
        mcp = Mock()
        registered_tools = []

        def mock_tool_decorator():
            def decorator(func):
                registered_tools.append(func)
                return func

            return decorator

        mcp.tool = mock_tool_decorator
        register_health_tools(mcp)

        # Find and call health_check tool
        health_check = next(
            (t for t in registered_tools if t.__name__ == "health_check"), None
        )
        assert health_check is not None

        result = await health_check()

        # Verify result structure
        assert "status" in result
        assert "version" in result
        assert "timestamp" in result
        assert "environment" in result
        assert "services" in result
        assert "mcp_server" in result

        assert result["status"] == "healthy"
        assert result["mcp_server"]["enabled"] is True
        assert result["mcp_server"]["running"] is True

    @pytest.mark.asyncio
    @patch("src.mcp_server.tools.health._check_services")
    @patch("src.mcp_server.mcp_app.get_mcp_status")
    async def test_health_check_tool_degraded(
        self, mock_mcp_status, mock_check_services
    ):
        """Test health_check tool returns degraded status when services are down"""
        # Setup mocks with some services down
        mock_check_services.return_value = {
            "postgres": True,
            "redis": False,
            "qdrant": True,
            "ollama": False,
        }
        mock_mcp_status.return_value = {
            "enabled": True,
            "running": True,
            "connection_state": "connected",
        }

        # Register and call tool
        mcp = Mock()
        registered_tools = []

        def mock_tool_decorator():
            def decorator(func):
                registered_tools.append(func)
                return func

            return decorator

        mcp.tool = mock_tool_decorator
        register_health_tools(mcp)

        health_check = next(
            (t for t in registered_tools if t.__name__ == "health_check"), None
        )
        result = await health_check()

        assert result["status"] == "degraded"

    @pytest.mark.asyncio
    @patch("src.mcp_server.mcp_app.get_mcp_status")
    async def test_server_info_tool(self, mock_mcp_status):
        """Test server_info tool returns correct information"""
        mock_mcp_status.return_value = {
            "enabled": True,
            "running": True,
            "connection_state": "connected",
        }

        # Register and call tool
        mcp = Mock()
        registered_tools = []

        def mock_tool_decorator():
            def decorator(func):
                registered_tools.append(func)
                return func

            return decorator

        mcp.tool = mock_tool_decorator
        register_health_tools(mcp)

        server_info = next(
            (t for t in registered_tools if t.__name__ == "server_info"), None
        )
        assert server_info is not None

        result = await server_info()

        # Verify result structure
        assert "name" in result
        assert "version" in result
        assert "description" in result
        assert "environment" in result
        assert "mcp_enabled" in result
        assert "mcp_connection_state" in result
        assert "timestamp" in result


class TestCapabilityTools:
    """Test capabilities tool endpoints"""

    def test_register_capability_tools(self, mock_mcp):
        """Test that capability tools are registered successfully"""
        register_capability_tools(mock_mcp)

        # Verify tool decorator was called
        assert mock_mcp.tool.called

    @pytest.mark.asyncio
    @patch("src.mcp_server.mcp_app.get_mcp_status")
    async def test_list_capabilities_tool(self, mock_mcp_status):
        """Test list_capabilities tool returns correct structure"""
        mock_mcp_status.return_value = {
            "enabled": True,
            "running": True,
            "connection_state": "connected",
        }

        # Register and call tool
        mcp = Mock()
        registered_tools = []

        def mock_tool_decorator():
            def decorator(func):
                registered_tools.append(func)
                return func

            return decorator

        mcp.tool = mock_tool_decorator
        register_capability_tools(mcp)

        list_capabilities = next(
            (t for t in registered_tools if t.__name__ == "list_capabilities"), None
        )
        assert list_capabilities is not None

        result = await list_capabilities()

        # Verify result structure
        assert "server" in result
        assert "capabilities" in result
        assert "tools" in result
        assert "features" in result
        assert "timestamp" in result

        # Verify server info
        assert result["server"]["name"] == settings.mcp_server_name
        assert result["server"]["version"] == settings.mcp_server_version

        # Verify tools list
        assert isinstance(result["tools"], list)
        assert len(result["tools"]) > 0

        # Verify each tool has required fields
        for tool in result["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "category" in tool

    @pytest.mark.asyncio
    async def test_get_configuration_tool(self):
        """Test get_configuration tool returns correct structure"""
        # Register and call tool
        mcp = Mock()
        registered_tools = []

        def mock_tool_decorator():
            def decorator(func):
                registered_tools.append(func)
                return func

            return decorator

        mcp.tool = mock_tool_decorator
        register_capability_tools(mcp)

        get_configuration = next(
            (t for t in registered_tools if t.__name__ == "get_configuration"), None
        )
        assert get_configuration is not None

        result = await get_configuration()

        # Verify result structure
        assert "server" in result
        assert "mcp" in result
        assert "performance" in result
        assert "logging" in result
        assert "hardware_requirements" in result
        assert "timestamp" in result

        # Verify server configuration
        assert result["server"]["host"] == settings.host
        assert result["server"]["port"] == settings.port

        # Verify MCP configuration
        assert result["mcp"]["enabled"] == settings.mcp_enabled
        assert result["mcp"]["server_name"] == settings.mcp_server_name

        # Verify performance settings
        assert (
            result["performance"]["max_search_results"] == settings.max_search_results
        )

        # Verify hardware requirements
        assert (
            result["hardware_requirements"]["min_memory_gb"] == settings.min_memory_gb
        )


class TestToolErrorHandling:
    """Test error handling in MCP tools"""

    @pytest.mark.asyncio
    @patch("src.mcp_server.tools.health._check_services")
    async def test_health_check_error_handling(self, mock_check_services):
        """Test that health_check handles errors gracefully"""
        # Force an error
        mock_check_services.side_effect = Exception("Service check failed")

        # Register and call tool
        mcp = Mock()
        registered_tools = []

        def mock_tool_decorator():
            def decorator(func):
                registered_tools.append(func)
                return func

            return decorator

        mcp.tool = mock_tool_decorator
        register_health_tools(mcp)

        health_check = next(
            (t for t in registered_tools if t.__name__ == "health_check"), None
        )
        result = await health_check()

        # Should return error response instead of raising
        assert "status" in result
        assert result["status"] == "error"
        assert "error" in result
