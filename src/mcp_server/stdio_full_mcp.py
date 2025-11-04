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

# Configure logging early
configure_logging(level=settings.log_level, fmt=settings.log_format)
logger = logging.getLogger(__name__)


async def initialize_services():
    """
    Initialize Qdrant and embedding services

    This is critical for MCP stdio server to function properly.
    The FastAPI server initializes these in its lifespan handler,
    but the stdio server needs explicit initialization.

    Returns:
        bool: True if initialization successful
    """
    logger.info("Initializing vector database services...")

    try:
        # Import services
        from src.vector_db.qdrant_client import connect_qdrant
        from src.vector_db.embeddings import initialize_embeddings

        # Connect to Qdrant
        logger.info("Connecting to Qdrant...")
        qdrant_connected = await connect_qdrant()
        if qdrant_connected:
            logger.info("✅ Qdrant connection initialized successfully")
        else:
            logger.warning("⚠️  Qdrant connection failed, some features may not work")

        # Initialize embeddings (this takes ~12 seconds)
        logger.info("Loading embedding model (this may take 10-15 seconds)...")
        await initialize_embeddings()
        logger.info("✅ Embedding service initialized successfully")

        logger.info("All services initialized successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}", exc_info=True)
        logger.warning("MCP server will start but search/vector tools may not work")
        return False


def main():
    logger.info("Starting FULL STDIO MCP server (all tools)...")

    # Create event loop for service initialization
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Initialize services BEFORE creating MCP server
    logger.info("Initializing services (this may take 15-20 seconds)...")
    try:
        success = loop.run_until_complete(initialize_services())
        if not success:
            logger.warning("Service initialization incomplete, continuing anyway...")
    except Exception as e:
        logger.error(f"Service initialization failed: {e}", exc_info=True)
        logger.warning("Continuing without full service initialization...")

    # Create MCP server and FastMCP instance
    logger.info("Creating MCP server instance...")
    server = MCPServer()
    mcp = server.create_server()

    # Register ALL tools (context-aware, indexing, search, etc.)
    logger.info("Registering MCP tools...")
    server.register_tools()

    # Mark as running/listening for status reporting
    server.is_running = True
    server.connection_state = "listening"

    logger.info("MCP server ready and listening for connections")

    try:
        logger.info("Starting FastMCP stdio transport...")
        # FastMCP's run() method manages its own event loop via anyio
        # It should be called directly, not awaited
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception:
        logger.exception("Unhandled error in stdio MCP server")
        raise
    finally:
        # MCP server manages its own lifecycle when running in stdio mode
        # No need for explicit shutdown here as it's handled by FastMCP
        pass


if __name__ == "__main__":
    # Call main() directly since FastMCP manages its own event loop
    main()

