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
    Initialize critical services during MCP server startup

    Strategy:
    - Qdrant: Initialize now (fast, ~0.5s) - just TCP connection
    - Embeddings: Lazy-load on first use (slow, ~30s) - model loading + GPU init
    - Collection: Validate dimensions match embedding model

    This ensures:
    - Fast startup (<2 seconds)
    - Qdrant ready immediately for vector search tools
    - No 30+ second delay from embedding model loading
    - No dimension mismatch errors during search

    Returns:
        bool: True if Qdrant initialization successful
    """
    logger.info("Initializing vector database services...")

    try:
        # Initialize Qdrant connection (fast - just TCP connection to port 6333)
        logger.info("Connecting to Qdrant vector database...")
        from src.vector_db.qdrant_client import connect_qdrant

        qdrant_connected = await connect_qdrant()

        if qdrant_connected:
            logger.info("✅ Qdrant connected successfully - vector search tools ready")

            # Validate/fix collection dimensions to match embedding model
            logger.info("Validating vector collection dimensions...")
            from src.vector_db.vector_store import vector_store
            from src.config.settings import settings

            # Use the configured vector size (default: 384 for all-MiniLM-L6-v2)
            vector_size = settings.qdrant_vector_size

            # Ensure collection exists with correct dimensions
            # This will auto-fix dimension mismatches by recreating the collection
            collection_ready = await vector_store.ensure_collection(
                vector_size=vector_size,
                auto_fix_mismatch=True
            )

            if collection_ready:
                logger.info(f"✅ Vector collection ready with {vector_size} dimensions")
            else:
                logger.warning("⚠️ Vector collection validation failed")
                logger.warning("   Vector search may not work correctly")
        else:
            logger.warning("⚠️ Qdrant connection failed - vector search tools may not work")
            logger.warning("   Make sure Qdrant is running: docker-compose up -d qdrant")
            logger.warning("   Or check connection at http://localhost:6333")

        # Embeddings remain lazy-loaded (slow - model loading + GPU init ~30s)
        # They will initialize automatically on first use
        logger.info("✅ Embedding service will initialize on first use (lazy loading)")

        logger.info("Service initialization complete")
        return qdrant_connected

    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}", exc_info=True)
        logger.warning("MCP server will start but vector search tools may not work")
        logger.warning("Check that Qdrant is running on port 6333")
        return False


def main():
    logger.info("Starting FULL STDIO MCP server (all tools)...")

    # Log diagnostic information about the environment
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"CLAUDE_PROJECT_DIR: {os.environ.get('CLAUDE_PROJECT_DIR', 'NOT SET')}")
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'NOT SET')}")
    logger.info(f"Indexed paths from settings: {settings.indexed_paths}")

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

