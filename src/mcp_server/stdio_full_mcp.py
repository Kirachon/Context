#!/usr/bin/env python3
"""
Full STDIO MCP Server

Starts FastMCP over stdio and registers ALL tools (including context-aware tools).
Use this entrypoint for Claude Code CLI stdio transport.
"""
import asyncio
import sys
import os
import logging

# Prefer PYTHONPATH from environment; fall back to repo root if running in Docker
if '/app' not in sys.path:
    sys.path.insert(0, os.getcwd())

from src.mcp_server.mcp_app import MCPServer
from src.config.settings import settings
from src.logging.manager import configure_logging

# Configure logging early - MUST use stderr for MCP stdio to avoid corrupting protocol
configure_logging(level=settings.log_level, fmt=settings.log_format, use_stderr=True)
logger = logging.getLogger(__name__)


async def initialize_services():
    """
    Initialize services (all services are now lazy-loaded for fast startup)

    This is critical for MCP stdio server to function properly.
    The FastAPI server initializes these in its lifespan handler,
    but the stdio server needs explicit initialization.

    Returns:
        bool: True if initialization successful
    """
    logger.info("Initializing vector database services...")

    try:
        # NOTE: Both Qdrant and Embeddings are now lazy-loaded on first use
        # This prevents Claude Code CLI from timing out during initialization
        # Services will be initialized automatically when first accessed
        logger.info("✅ Qdrant connection will be established on first use (lazy loading)")
        logger.info("✅ Embedding service will be initialized on first use (lazy loading)")

        logger.info("All services initialized successfully (lazy loading enabled)")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}", exc_info=True)
        logger.warning("MCP server will start but search/vector tools may not work")
        return False


def main():
    logger.info("Starting FULL STDIO MCP server (all tools)...")

    # Redirect stdout to stderr during initialization to prevent pollution
    # This prevents tqdm progress bars and other output from corrupting MCP protocol
    original_stdout = sys.stdout
    sys.stdout = sys.stderr

    try:
        # Create event loop for service initialization
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Initialize services BEFORE creating MCP server (fast startup - embeddings lazy-loaded)
        logger.info("Initializing services...")
        try:
            success = loop.run_until_complete(initialize_services())
            if not success:
                logger.warning("Service initialization incomplete, continuing anyway...")
        except Exception as e:
            logger.error(f"Service initialization failed: {e}", exc_info=True)
            logger.warning("Continuing without full service initialization...")

        # Use the GLOBAL MCP server instance so health checks work correctly
        logger.info("Using global MCP server instance...")
        from src.mcp_server.mcp_app import mcp_server

        mcp = mcp_server.create_server()

        # Register ALL tools (context-aware, indexing, search, etc.)
        logger.info("Registering MCP tools...")
        mcp_server.register_tools()

        # Mark as running/listening for status reporting
        mcp_server.is_running = True
        mcp_server.connection_state = "listening"

        logger.info("MCP server ready and listening for connections")

    finally:
        # Restore stdout for MCP protocol communication
        sys.stdout = original_stdout

    try:
        logger.info("Starting FastMCP stdio transport...")
        # FastMCP's run() method manages its own event loop via anyio
        # It should be called directly, not awaited
        # Disable banner to avoid polluting stdout (MCP protocol channel)
        os.environ["FASTMCP_NO_BANNER"] = "1"
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        mcp_server.is_running = False
        mcp_server.connection_state = "disconnected"
    except Exception:
        logger.exception("Unhandled error in stdio MCP server")
        mcp_server.is_running = False
        mcp_server.connection_state = "error"
        raise
    finally:
        # MCP server manages its own lifecycle when running in stdio mode
        # No need for explicit shutdown here as it's handled by FastMCP
        pass


if __name__ == "__main__":
    # Call main() directly since FastMCP manages its own event loop
    main()

