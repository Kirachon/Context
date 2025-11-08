#!/usr/bin/env python3
"""
HTTP MCP Server Entry Point

Starts FastMCP over HTTP transport for improved reliability and multi-project availability.
This persistent server approach solves connection issues with stdio transport.

Key Benefits:
- Single persistent server instance (no process-per-session overhead)
- Shared Qdrant connection across all projects
- Embeddings loaded once in memory
- Better reliability when switching between projects
- Connection pooling and retry logic

Usage:
    python -m src.mcp_server.http_server

Or with uvicorn directly:
    uvicorn src.mcp_server.http_server:create_app --factory --host 127.0.0.1 --port 8000

Configuration:
    Update ~/.claude.json to use HTTP transport:
    {
      "mcpServers": {
        "context": {
          "type": "http",
          "url": "http://localhost:8000/"
        }
      }
    }
"""
import asyncio
import sys
import os
import logging
import uvicorn

# Prefer PYTHONPATH from environment; fall back to repo root if running in Docker
if '/app' not in sys.path:
    sys.path.insert(0, os.getcwd())

from src.config.settings import settings
from src.logging.manager import configure_logging

# Configure logging - HTTP mode can use stdout safely
configure_logging(level=settings.log_level, fmt=settings.log_format, use_stderr=False)
logger = logging.getLogger(__name__)


async def initialize_services():
    """
    Initialize critical services during MCP server startup
    
    This is identical to stdio_full_mcp.py initialization but runs once
    for the persistent HTTP server instead of per-connection.
    
    Returns:
        bool: True if Qdrant initialization successful
    """
    logger.info("Initializing core services (Qdrant, Embeddings, FileMonitor)...")

    try:
        # 1) Initialize Qdrant connection (fast)
        logger.info("Connecting to Qdrant vector database...")
        from src.vector_db.qdrant_client import connect_qdrant
        from src.vector_db.vector_store import vector_store

        qdrant_connected = await connect_qdrant()

        if qdrant_connected:
            logger.info("✅ Qdrant connected successfully - vector search tools ready")

            # Validate collection dimensions WITHOUT auto-deleting existing collections.
            # If mismatch is detected, move this local server to a size-suffixed collection
            # to avoid disrupting the Docker/production collection.
            vector_size = settings.qdrant_vector_size
            logger.info("Validating vector collection dimensions (expected dim=%s)...", vector_size)

            collection_ready = await vector_store.ensure_collection(
                vector_size=vector_size,
                auto_fix_mismatch=False  # be safe; do not drop existing collections
            )

            if not collection_ready:
                base_name = getattr(settings, "qdrant_collection", "context_vectors")
                safe_name = f"{base_name}_{vector_size}"
                logger.warning(
                    "⚠️ Vector collection dimension mismatch detected. "
                    "Switching this local server to a dedicated collection: %s",
                    safe_name,
                )
                # Switch the global vector store to a safe, size-suffixed collection
                vector_store.collection_name = safe_name
                # Create the new collection with the correct dimensions
                created = await vector_store.ensure_collection(
                    vector_size=vector_size,
                    auto_fix_mismatch=True
                )
                if created:
                    logger.info("✅ Created collection '%s' with %d dimensions", safe_name, vector_size)
                else:
                    logger.warning("⚠️ Failed to create collection '%s'", safe_name)
            else:
                logger.info("✅ Vector collection ready with %d dimensions", vector_size)
        else:
            logger.warning("⚠️ Qdrant connection failed - vector search tools may not work")
            logger.warning("   Make sure Qdrant is running: docker-compose up -d qdrant")
            logger.warning("   Or check connection at http://localhost:6333")

        # 2) Initialize PostgreSQL (optional)
        try:
            logger.info("Initializing database (optional)...")
            from src.indexing.models import init_db
            init_db()
            logger.info("✅ Database initialized (or will be skipped by indexer on failure)")
        except Exception as db_e:
            logger.warning(
                "PostgreSQL unavailable or failed to initialize; proceeding in vector-only mode: %s",
                db_e,
            )

        # 3) Initialize embeddings explicitly so the queue can run immediately
        try:
            logger.info("Initializing embedding service...")
            from src.vector_db.embeddings import initialize_embeddings
            await initialize_embeddings()
            logger.info("✅ Embedding service initialized successfully")
        except Exception as emb_e:
            logger.error("❌ Failed to initialize embedding service: %s", emb_e, exc_info=True)
            # We continue; queue will retry and logs will show the error

        # 4) Start file monitor with queue callback
        try:
            logger.info("Starting file monitor...")
            from src.indexing.file_monitor import start_file_monitor
            from src.indexing.queue import queue_file_change
            await start_file_monitor(on_change_callback=queue_file_change)
            logger.info("✅ File monitor started successfully")
        except Exception as fm_e:
            logger.error("❌ Failed to start FileMonitor: %s", fm_e, exc_info=True)

        # 5) Initial indexing (synchronous kick-off)
        # In HTTP transport, ASGI startup events may not always fire depending on the wrapper.
        # To guarantee progress, we perform a one-time initial indexing pass here.
        try:
            logger.info("Kicking off initial indexing synchronously (one-time)...")
            from src.indexing.initial_indexer import run_initial_indexing
            from src.indexing.queue import queue_file_change, indexing_queue
            # Scan and enqueue all files
            await run_initial_indexing(on_file_callback=queue_file_change)
            # Process the queue immediately so vectors start flowing into Qdrant
            await indexing_queue.process_queue()
            logger.info("✅ Initial indexing pass completed")
        except Exception as ie:
            logger.warning("Initial indexing kick-off failed; background monitor may still pick up changes: %s", ie, exc_info=True)

        logger.info("Service initialization complete")
        return qdrant_connected

    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}", exc_info=True)
        logger.warning("MCP server will start but vector search tools may not work")
        logger.warning("Check that Qdrant is running on port 6333")
        return False


def create_app():
    """
    Create the ASGI application for HTTP transport
    
    This function is called by uvicorn to create the application instance.
    It initializes services and creates the FastMCP HTTP app.
    
    Returns:
        StarletteWithLifespan: ASGI application instance
    """
    logger.info("Creating HTTP MCP server application...")
    logger.info(f"Server: {settings.mcp_server_name} v{settings.mcp_server_version}")
    
    # Log diagnostic information
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"CLAUDE_PROJECT_DIR: {os.environ.get('CLAUDE_PROJECT_DIR', 'NOT SET')}")
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'NOT SET')}")
    logger.info(f"Indexed paths from settings: {settings.indexed_paths}")
    
    # Initialize services synchronously (create event loop if needed)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    logger.info("Initializing services...")
    try:
        success = loop.run_until_complete(initialize_services())
        if not success:
            logger.warning("Service initialization incomplete, continuing anyway...")
    except Exception as e:
        logger.error(f"Service initialization failed: {e}", exc_info=True)
        logger.warning("Continuing without full service initialization...")
    
    # Use the GLOBAL MCP server instance
    logger.info("Creating MCP server instance...")
    from src.mcp_server.mcp_app import mcp_server
    
    mcp = mcp_server.create_server()
    
    # Register ALL tools
    logger.info("Registering MCP tools...")
    mcp_server.register_tools()
    
    # Mark as running
    mcp_server.is_running = True
    mcp_server.connection_state = "listening"
    
    logger.info("Creating streamable HTTP ASGI app at path '/'")
    app = mcp.streamable_http_app(path="/")
    logger.info("✅ MCP HTTP app ready")
    return app


def main():
    """
    Main entry point for running the HTTP server directly

    This is used when running: python -m src.mcp_server.http_server
    """
    logger.info("Starting Context MCP HTTP Server...")
    logger.info(f"Server will be available at: http://0.0.0.0:8000/")
    logger.info("Press Ctrl+C to stop the server")

    # Create the ASGI app and run with uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()

