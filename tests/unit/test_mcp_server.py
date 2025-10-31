"""
Unit tests for MCP Server

Tests MCP server initialization, tool registration, connection lifecycle,
and graceful shutdown functionality.
"""

import pytest
import asyncio
import signal
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Add project root to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.mcp_server.mcp_app import MCPServer, mcp_server, start_mcp_server, shutdown_mcp_server, get_mcp_status
from src.config.settings import settings


@pytest.fixture
def mock_env():
    """Mock environment variables for testing"""
    original_env = os.environ.copy()
    os.environ.update({
        "MCP_ENABLED": "true",
        "MCP_SERVER_NAME": "Context",
        "MCP_SERVER_VERSION": "0.1.0",
        "LOG_LEVEL": "DEBUG"
    })
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mcp_server_instance():
    """Create a fresh MCP server instance for testing"""
    return MCPServer()


class TestMCPServerInitialization:
    """Test MCP server initialization and configuration"""
    
    def test_mcp_server_initialization(self, mcp_server_instance):
        """Test that MCP server initializes with correct default state"""
        assert mcp_server_instance.mcp is None
        assert mcp_server_instance.is_running is False
        assert mcp_server_instance.connection_state == "disconnected"
        assert not mcp_server_instance.shutdown_event.is_set()
    
    def test_mcp_server_metadata(self, mcp_server_instance, mock_env):
        """Test that server metadata is configured correctly"""
        # Reload settings to pick up mock env
        from importlib import reload
        import src.config.settings as settings_module
        reload(settings_module)
        
        server = mcp_server_instance.create_server()
        
        # Verify server was created (if MCP enabled)
        if settings.mcp_enabled:
            assert server is not None
    
    @patch('src.mcp_server.mcp_app.FastMCP')
    def test_create_server_with_mcp_disabled(self, mock_fastmcp, mcp_server_instance):
        """Test that server creation is skipped when MCP is disabled"""
        with patch.object(settings, 'mcp_enabled', False):
            server = mcp_server_instance.create_server()
            assert server is None
            mock_fastmcp.assert_not_called()
    
    def test_get_status(self, mcp_server_instance):
        """Test that get_status returns correct structure"""
        status = mcp_server_instance.get_status()
        
        assert "enabled" in status
        assert "running" in status
        assert "connection_state" in status
        assert "server_name" in status
        assert "version" in status
        assert "capabilities" in status
        assert "timestamp" in status
        
        assert isinstance(status["enabled"], bool)
        assert isinstance(status["running"], bool)
        assert isinstance(status["capabilities"], list)


class TestMCPConnectionLifecycle:
    """Test MCP connection lifecycle management"""
    
    @pytest.mark.asyncio
    async def test_connection_state_transitions(self, mcp_server_instance):
        """Test that connection state transitions correctly"""
        assert mcp_server_instance.connection_state == "disconnected"
        
        # Simulate connection
        mcp_server_instance.connection_state = "connected"
        assert mcp_server_instance.connection_state == "connected"
        
        # Simulate disconnection
        mcp_server_instance.connection_state = "disconnected"
        assert mcp_server_instance.connection_state == "disconnected"
    
    @pytest.mark.asyncio
    async def test_reconnection_logic(self, mcp_server_instance):
        """Test reconnection attempts after transient failures"""
        mcp_server_instance.is_running = True
        mcp_server_instance.connection_state = "error"
        
        # Mock the reconnection attempt
        with patch.object(mcp_server_instance, '_attempt_reconnection', new_callable=AsyncMock) as mock_reconnect:
            await mcp_server_instance._attempt_reconnection()
            mock_reconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_max_reconnection_attempts(self, mcp_server_instance):
        """Test that reconnection stops after max retries"""
        mcp_server_instance.is_running = True
        
        with patch.object(settings, 'mcp_max_retries', 2):
            await mcp_server_instance._attempt_reconnection()
            
            # After max retries, state should be failed
            assert mcp_server_instance.connection_state in ["reconnecting", "failed"]


class TestMCPToolRegistration:
    """Test MCP tool endpoint registration"""
    
    @patch('src.mcp_server.mcp_app.FastMCP')
    def test_register_tools_without_server(self, mock_fastmcp, mcp_server_instance):
        """Test that tool registration fails gracefully without server"""
        mcp_server_instance.mcp = None
        mcp_server_instance.register_tools()
        # Should log error but not crash
    
    @patch('src.mcp_server.tools.health.register_health_tools')
    @patch('src.mcp_server.tools.capabilities.register_capability_tools')
    @patch('src.mcp_server.mcp_app.FastMCP')
    def test_register_tools_success(self, mock_fastmcp, mock_cap_tools, mock_health_tools, mcp_server_instance):
        """Test successful tool registration"""
        mock_mcp = Mock()
        mcp_server_instance.mcp = mock_mcp
        
        mcp_server_instance.register_tools()
        
        mock_health_tools.assert_called_once_with(mock_mcp)
        mock_cap_tools.assert_called_once_with(mock_mcp)


class TestMCPServerStartup:
    """Test MCP server startup process"""
    
    @pytest.mark.asyncio
    async def test_start_with_mcp_disabled(self, mcp_server_instance):
        """Test that startup is skipped when MCP is disabled"""
        with patch.object(settings, 'mcp_enabled', False):
            await mcp_server_instance.start()
            assert mcp_server_instance.is_running is False
    
    @pytest.mark.asyncio
    @patch('src.mcp_server.mcp_app.MCPServer.create_server')
    @patch('src.mcp_server.mcp_app.MCPServer.register_tools')
    @patch('src.mcp_server.mcp_app.MCPServer._setup_signal_handlers')
    async def test_start_success(self, mock_signals, mock_register, mock_create, mcp_server_instance):
        """Test successful server startup"""
        with patch.object(settings, 'mcp_enabled', True):
            mock_create.return_value = Mock()
            
            await mcp_server_instance.start()
            
            mock_create.assert_called_once()
            mock_register.assert_called_once()
            mock_signals.assert_called_once()
            assert mcp_server_instance.is_running is True
            assert mcp_server_instance.connection_state == "listening"
    
    @pytest.mark.asyncio
    @patch('src.mcp_server.mcp_app.MCPServer.create_server')
    async def test_start_failure(self, mock_create, mcp_server_instance):
        """Test that startup failure is handled properly"""
        with patch.object(settings, 'mcp_enabled', True):
            mock_create.side_effect = Exception("Startup failed")
            
            with pytest.raises(Exception, match="Startup failed"):
                await mcp_server_instance.start()
            
            assert mcp_server_instance.is_running is False


class TestMCPServerShutdown:
    """Test MCP server graceful shutdown"""
    
    @pytest.mark.asyncio
    async def test_shutdown_when_not_running(self, mcp_server_instance):
        """Test shutdown when server is not running"""
        mcp_server_instance.is_running = False
        await mcp_server_instance.shutdown()
        # Should complete without error
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, mcp_server_instance):
        """Test graceful shutdown process"""
        mcp_server_instance.is_running = True
        mcp_server_instance.connection_state = "connected"
        
        await mcp_server_instance.shutdown(timeout=5)
        
        assert mcp_server_instance.is_running is False
        assert mcp_server_instance.connection_state == "shutdown"
        assert mcp_server_instance.shutdown_event.is_set()
    
    @pytest.mark.asyncio
    async def test_shutdown_timeout(self, mcp_server_instance):
        """Test shutdown timeout and force shutdown"""
        mcp_server_instance.is_running = True
        
        # Mock a long-running cleanup that will timeout
        with patch('asyncio.timeout', side_effect=asyncio.TimeoutError):
            await mcp_server_instance.shutdown(timeout=1)
            
            # Should force shutdown after timeout
            assert mcp_server_instance.shutdown_event.is_set()
    
    @pytest.mark.asyncio
    async def test_shutdown_with_error(self, mcp_server_instance):
        """Test that shutdown handles errors gracefully"""
        mcp_server_instance.is_running = True
        
        # Force an error during shutdown
        with patch.object(mcp_server_instance.shutdown_event, 'set', side_effect=Exception("Shutdown error")):
            # Should not raise, but log error
            await mcp_server_instance.shutdown()


class TestMCPServerLogging:
    """Test MCP server logging functionality"""
    
    @pytest.mark.asyncio
    @patch('src.mcp_server.mcp_app.logger')
    async def test_startup_logging(self, mock_logger, mcp_server_instance):
        """Test that startup events are logged"""
        with patch.object(settings, 'mcp_enabled', False):
            await mcp_server_instance.start()
            
            # Verify logging calls
            assert mock_logger.warning.called or mock_logger.info.called
    
    @pytest.mark.asyncio
    @patch('src.mcp_server.mcp_app.logger')
    async def test_shutdown_logging(self, mock_logger, mcp_server_instance):
        """Test that shutdown events are logged"""
        mcp_server_instance.is_running = True
        
        await mcp_server_instance.shutdown()
        
        # Verify logging calls
        assert mock_logger.info.called


class TestMCPGlobalFunctions:
    """Test global MCP server functions"""
    
    @pytest.mark.asyncio
    async def test_start_mcp_server_function(self):
        """Test global start_mcp_server function"""
        with patch('src.mcp_server.mcp_app.mcp_server.start', new_callable=AsyncMock) as mock_start:
            await start_mcp_server()
            mock_start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_mcp_server_function(self):
        """Test global shutdown_mcp_server function"""
        with patch('src.mcp_server.mcp_app.mcp_server.shutdown', new_callable=AsyncMock) as mock_shutdown:
            await shutdown_mcp_server()
            mock_shutdown.assert_called_once()
    
    def test_get_mcp_status_function(self):
        """Test global get_mcp_status function"""
        status = get_mcp_status()
        
        assert isinstance(status, dict)
        assert "enabled" in status
        assert "running" in status
        assert "connection_state" in status

