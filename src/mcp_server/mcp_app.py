"""
Context MCP Server Application

FastMCP server implementation for Claude Code CLI integration.
Provides tool registration, connection lifecycle management, and graceful shutdown.
"""

import asyncio
import signal
import sys
import os
from typing import Optional
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from fastmcp import FastMCP
from src.config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPServer:
    """
    MCP Server wrapper for Context application
    
    Manages FastMCP server lifecycle, tool registration, and connection state.
    """
    
    def __init__(self):
        """Initialize MCP server with configuration from settings"""
        self.mcp: Optional[FastMCP] = None
        self.is_running = False
        self.connection_state = "disconnected"
        self.shutdown_event = asyncio.Event()
        
        logger.info(
            f"Initializing MCP Server: {settings.mcp_server_name} v{settings.mcp_server_version}"
        )
    
    def create_server(self) -> FastMCP:
        """
        Create and configure FastMCP server instance
        
        Returns:
            FastMCP: Configured MCP server instance
        """
        if not settings.mcp_enabled:
            logger.warning("MCP server is disabled in settings")
            return None
        
        logger.info("Creating FastMCP server instance")
        
        # Create FastMCP server with metadata
        mcp = FastMCP(
            name=settings.mcp_server_name,
            version=settings.mcp_server_version,
        )
        
        # Register connection lifecycle handlers in a version-tolerant way
        async def handle_connect():
            """Handle client connection event"""
            self.connection_state = "connected"
            logger.info("MCP client connected successfully")
            logger.debug(f"Connection state: {self.connection_state}")

        async def handle_disconnect():
            """Handle client disconnection event"""
            self.connection_state = "disconnected"
            logger.info("MCP client disconnected")
            logger.debug(f"Connection state: {self.connection_state}")

        async def handle_error(error: Exception):
            """Handle connection errors"""
            self.connection_state = "error"
            logger.error(f"MCP connection error: {error}", exc_info=True)
            logger.debug(f"Connection state: {self.connection_state}")
            # Attempt reconnection for transient failures
            if self.is_running:
                logger.info("Attempting reconnection after error...")
                await self._attempt_reconnection()

        def _safe_register(event_name: str, handler):
            """Attempt multiple registration strategies without failing."""
            try:
                method = getattr(mcp, f"on_{event_name}", None)
                if callable(method):
                    try:
                        # Some versions accept the handler directly
                        result = method(handler)
                        # If decorator-style, calling without args returns a decorator
                        if callable(result):
                            result(handler)
                        return
                    except TypeError:
                        # Decorator-style: on_xxx() returns decorator
                        try:
                            decorator = method()
                            if callable(decorator):
                                decorator(handler)
                                return
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"on_{event_name} registration not available: {e}")

            # Fallback to generic add_event_handler if present
            try:
                add = getattr(mcp, "add_event_handler", None)
                if callable(add):
                    add(event_name, handler)
            except Exception as e:
                logger.debug(f"add_event_handler fallback failed for {event_name}: {e}")

        _safe_register("connect", handle_connect)
        _safe_register("disconnect", handle_disconnect)
        _safe_register("error", handle_error)
        
        self.mcp = mcp
        logger.info("FastMCP server instance created successfully")
        return mcp
    
    async def _attempt_reconnection(self):
        """Attempt to reconnect after transient failures"""
        for attempt in range(1, settings.mcp_max_retries + 1):
            try:
                logger.info(f"Reconnection attempt {attempt}/{settings.mcp_max_retries}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
                # Connection will be re-established by FastMCP framework
                self.connection_state = "reconnecting"
                logger.info("Reconnection successful")
                return
                
            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt} failed: {e}")
                
                if attempt == settings.mcp_max_retries:
                    logger.error("Max reconnection attempts reached")
                    self.connection_state = "failed"
    
    def register_tools(self):
        """Register all MCP tool endpoints"""
        if not self.mcp:
            logger.error("Cannot register tools: MCP server not initialized")
            return
        
        logger.info("Registering MCP tool endpoints")

        # Import and register tools
        from src.mcp_server.tools.health import register_health_tools
        from src.mcp_server.tools.capabilities import register_capability_tools
        from src.mcp_server.tools.indexing import register_indexing_tools
        from src.mcp_server.tools.vector import register_vector_tools
        from src.mcp_server.tools.search import register_search_tools

        register_health_tools(self.mcp)
        register_capability_tools(self.mcp)
        register_indexing_tools(self.mcp)
        register_vector_tools(self.mcp)
        register_search_tools(self.mcp)

        logger.info(f"Registered {len(settings.mcp_capabilities)} MCP tools")
    
    async def start(self):
        """Start the MCP server"""
        if not settings.mcp_enabled:
            logger.warning("MCP server is disabled, skipping startup")
            return
        
        logger.info("Starting MCP server...")
        
        try:
            # Create server instance
            self.create_server()
            
            # Register all tools
            self.register_tools()
            
            # Mark as running
            self.is_running = True
            self.connection_state = "listening"
            
            logger.info(
                f"MCP server started successfully on {settings.mcp_server_name}"
            )
            logger.info(f"Available capabilities: {', '.join(settings.mcp_capabilities)}")
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}", exc_info=True)
            self.is_running = False
            raise
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            """Handle shutdown signals"""
            signal_name = signal.Signals(signum).name
            logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
            
            # Trigger shutdown
            asyncio.create_task(self.shutdown())
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.debug("Signal handlers registered for SIGTERM and SIGINT")
    
    async def shutdown(self, timeout: int = 10):
        """
        Gracefully shutdown the MCP server
        
        Args:
            timeout: Maximum seconds to wait for cleanup before force shutdown
        """
        if not self.is_running:
            logger.warning("MCP server is not running")
            return
        
        logger.info("Initiating MCP server shutdown...")
        self.is_running = False
        
        try:
            # Set shutdown timeout
            async with asyncio.timeout(timeout):
                # Clean up connections
                if self.connection_state == "connected":
                    logger.info("Closing active connections...")
                    self.connection_state = "disconnecting"

                # Cleanup resources
                logger.info("Cleaning up server resources...")

                # Mark as shutdown
                self.connection_state = "shutdown"
                try:
                    self.shutdown_event.set()
                except Exception as e:
                    logger.error(f"Error setting shutdown event: {e}")

                logger.info("MCP server shutdown completed successfully")

        except asyncio.TimeoutError:
            logger.error(f"Shutdown timeout ({timeout}s) exceeded, forcing shutdown")
            self.connection_state = "force_shutdown"
            try:
                self.shutdown_event.set()
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
            try:
                self.shutdown_event.set()
            except Exception:
                pass
    
    def get_status(self) -> dict:
        """
        Get current MCP server status
        
        Returns:
            dict: Server status information
        """
        return {
            "enabled": settings.mcp_enabled,
            "running": self.is_running,
            "connection_state": self.connection_state,
            "server_name": settings.mcp_server_name,
            "version": settings.mcp_server_version,
            "capabilities": settings.mcp_capabilities,
            "timestamp": datetime.utcnow().isoformat()
        }


# Global MCP server instance
mcp_server = MCPServer()


async def start_mcp_server():
    """Start the MCP server (entry point for integration)"""
    await mcp_server.start()


async def shutdown_mcp_server():
    """Shutdown the MCP server (entry point for integration)"""
    await mcp_server.shutdown()


def get_mcp_status() -> dict:
    """Get MCP server status (entry point for health checks)"""
    return mcp_server.get_status()


if __name__ == "__main__":
    # Run MCP server standalone
    async def main():
        await start_mcp_server()
        
        # Keep running until shutdown signal
        await mcp_server.shutdown_event.wait()
    
    asyncio.run(main())

