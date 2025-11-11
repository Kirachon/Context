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
from pathlib import Path
from typing import Optional

# Prefer PYTHONPATH from environment; fall back to repo root if running in Docker
if '/app' not in sys.path:
    sys.path.insert(0, os.getcwd())

from src.config.settings import settings
from src.logging.manager import configure_logging

# Configure logging - HTTP mode can use stdout safely
configure_logging(level=settings.log_level, fmt=settings.log_format, use_stderr=False)
logger = logging.getLogger(__name__)

# Global workspace manager instance (None in single-project mode)
_workspace_manager: Optional["WorkspaceManager"] = None


def get_workspace_manager() -> Optional["WorkspaceManager"]:
    """
    Get the global workspace manager instance

    Returns:
        WorkspaceManager instance if in workspace mode, None otherwise
    """
    return _workspace_manager


def is_workspace_mode() -> bool:
    """
    Check if server is running in workspace mode

    Returns:
        True if workspace mode is active, False for single-project mode
    """
    return _workspace_manager is not None


def get_project(project_id: str):
    """
    Get a specific project from the workspace

    Args:
        project_id: Project identifier

    Returns:
        Project instance or None
    """
    if _workspace_manager:
        return _workspace_manager.get_project(project_id)
    return None


async def initialize_services():
    """
    Initialize critical services during MCP server startup

    Detects workspace mode via .context-workspace.json and initializes accordingly:
    - Workspace mode: Initialize WorkspaceManager for multi-project support
    - Single-project mode: Use existing initialization (backwards compatible)

    Returns:
        Optional[WorkspaceManager]: WorkspaceManager instance if in workspace mode, None otherwise
    """
    fast_startup = os.environ.get("FAST_STARTUP", "").lower() == "true"

    # Check for workspace configuration file
    workspace_file = Path.cwd() / ".context-workspace.json"

    if workspace_file.exists():
        # NEW: Workspace mode - multi-project support
        logger.info("Detected .context-workspace.json - initializing in WORKSPACE MODE")

        try:
            # Import workspace manager only when needed
            from src.workspace.manager import WorkspaceManager

            workspace_manager = WorkspaceManager(str(workspace_file))

            # Initialize workspace (lazy_load=False for full initialization)
            # In FAST_STARTUP mode, we still initialize but may skip indexing
            success = await workspace_manager.initialize(lazy_load=fast_startup)

            if success:
                logger.info("✅ Workspace initialized successfully")

                # In non-fast mode, start indexing and monitoring
                if not fast_startup:
                    logger.info("Starting workspace indexing and monitoring...")
                    # Index all projects
                    await workspace_manager.index_all_projects(parallel=True)
                    logger.info("✅ Workspace indexing complete")
                else:
                    logger.info("⚡ FAST_STARTUP: Skipping workspace indexing (will lazy-load on first use)")

                return workspace_manager
            else:
                logger.error("❌ Workspace initialization failed - falling back to single-project mode")
                # Fall through to single-project initialization

        except Exception as e:
            logger.error(f"❌ Error initializing workspace: {e}", exc_info=True)
            logger.warning("Falling back to single-project mode")
            # Fall through to single-project initialization

    # OLD: Single-project mode (backwards compatible)
    logger.info("Initializing in SINGLE-PROJECT MODE (no workspace detected)")

    if fast_startup:
        logger.info("FAST_STARTUP mode: performing minimal initialization for CI")
    else:
        logger.info("Initializing core services (Qdrant, Embeddings, FileMonitor)...")

    try:
        # 1) Initialize Qdrant connection (fast, always do this)
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

        # 2) Initialize PostgreSQL (optional, disabled by default)
        if getattr(settings, "postgres_enabled", False) and getattr(settings, "database_url", None):
            try:
                logger.info("Initializing PostgreSQL metadata store (optional)...")
                from src.indexing.models import init_db
                init_db()
                logger.info("✅ PostgreSQL initialized; metadata persistence enabled")
            except Exception as db_e:
                logger.warning(
                    "PostgreSQL unavailable or failed to initialize; proceeding in vector-only mode: %s",
                    db_e,
                )
        else:
            logger.info("PostgreSQL disabled; running in vector-only mode")

        # FAST_STARTUP: Skip expensive operations
        if fast_startup:
            logger.info("⚡ FAST_STARTUP: Skipping embeddings and file monitor (will lazy-load on first use)")
            logger.info("Service initialization complete (fast mode)")
            return None  # Single-project mode returns None

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

        logger.info("Service initialization complete (single-project mode)")
        return None  # Single-project mode returns None

    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}", exc_info=True)
        logger.warning("MCP server will start but vector search tools may not work")
        logger.warning("Check that Qdrant is running on port 6333")
        return None  # Return None on error (single-project mode fallback)


def create_app():
    """
    Create the ASGI application for HTTP transport

    This function is called by uvicorn to create the application instance.
    It initializes services and creates the FastMCP HTTP app.

    Returns:
        ASGI application instance
    """
    global _workspace_manager

    logger.info("Creating HTTP MCP server application...")
    logger.info(f"Server: {settings.mcp_server_name} v{settings.mcp_server_version}")

    # Log diagnostic information
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"CLAUDE_PROJECT_DIR: {os.environ.get('CLAUDE_PROJECT_DIR', 'NOT SET')}")
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'NOT SET')}")
    logger.info(f"Indexed paths from settings: {settings.indexed_paths}")

    # Initialize services synchronously (FAST_STARTUP just skips expensive parts internally)
    logger.info("Initializing services...")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        workspace_or_none = loop.run_until_complete(initialize_services())
        _workspace_manager = workspace_or_none

        if _workspace_manager:
            logger.info("✅ HTTP server initialized in WORKSPACE MODE")
        else:
            logger.info("✅ HTTP server initialized in SINGLE-PROJECT MODE")
    except Exception as e:
        logger.error(f"Service initialization failed: {e}", exc_info=True)
        logger.warning("Continuing without full service initialization...")
        _workspace_manager = None

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

