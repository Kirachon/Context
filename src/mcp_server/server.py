"""
Context MCP Server - Main Application Entry Point

This module provides the FastAPI application for the Context MCP server,
implementing health check endpoints and basic server functionality.
"""

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import sys
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Application metadata
APP_VERSION = "0.1.0"
APP_NAME = "Context"
APP_DESCRIPTION = "100% Offline AI Coding Assistant"

# Create FastAPI application
app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
async def startup_event():
    """Initialize MCP server and file monitor on application startup"""
    logger.info("FastAPI application starting up...")

    try:
        from src.mcp_server.mcp_app import start_mcp_server
        await start_mcp_server()
        logger.info("MCP server initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MCP server: {e}", exc_info=True)

    try:
        from src.indexing.file_monitor import start_file_monitor
        from src.indexing.queue import queue_file_change
        from src.indexing.models import init_db

        # Initialize database
        init_db()
        logger.info("Database initialized successfully")

        # Start file monitor with queue callback
        await start_file_monitor(on_change_callback=queue_file_change)
        logger.info("File monitor started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize file monitor: {e}", exc_info=True)

    try:
        from src.vector_db.qdrant_client import connect_qdrant
        from src.vector_db.embeddings import initialize_embeddings

        # Connect to Qdrant
        await connect_qdrant()
        logger.info("Qdrant connection initialized successfully")

        # Initialize embeddings
        await initialize_embeddings()
        logger.info("Embedding service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize vector database: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown MCP server and file monitor on application shutdown"""
    logger.info("FastAPI application shutting down...")

    try:
        from src.vector_db.qdrant_client import disconnect_qdrant
        await disconnect_qdrant()
        logger.info("Qdrant disconnected successfully")
    except Exception as e:
        logger.error(f"Error disconnecting from Qdrant: {e}", exc_info=True)

    try:
        from src.indexing.file_monitor import stop_file_monitor
        await stop_file_monitor()
        logger.info("File monitor stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping file monitor: {e}", exc_info=True)

    try:
        from src.mcp_server.mcp_app import shutdown_mcp_server
        await shutdown_mcp_server()
        logger.info("MCP server shutdown successfully")
    except Exception as e:
        logger.error(f"Error during MCP server shutdown: {e}", exc_info=True)


# Health check response model
class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    version: str
    timestamp: str
    environment: str
    services: dict
    mcp_server: dict = {}


@app.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint

    Returns the current health status of the Context server and its dependencies.

    Returns:
        HealthResponse: Health status information including version, environment, and service status
    """
    # Check service connectivity
    services_status = await check_services()

    # Get MCP server status
    try:
        from src.mcp_server.mcp_app import get_mcp_status
        mcp_status = get_mcp_status()
    except Exception as e:
        logger.warning(f"Could not get MCP status: {e}")
        mcp_status = {"enabled": False, "running": False, "connection_state": "unknown"}

    # Get Qdrant status
    try:
        from src.vector_db.qdrant_client import get_qdrant_status
        qdrant_status = await get_qdrant_status()
        services_status["qdrant"] = qdrant_status.get("connected", False)
    except Exception as e:
        logger.warning(f"Could not get Qdrant status: {e}")
        services_status["qdrant"] = False

    # Determine overall health
    all_healthy = all(services_status.values())
    health_status = "healthy" if all_healthy else "degraded"

    return HealthResponse(
        status=health_status,
        version=APP_VERSION,
        timestamp=datetime.utcnow().isoformat(),
        environment=os.getenv("ENVIRONMENT", "development"),
        services=services_status,
        mcp_server={
            "enabled": mcp_status.get("enabled", False),
            "running": mcp_status.get("running", False),
            "connection_state": mcp_status.get("connection_state", "unknown")
        }
    )


async def check_services() -> dict:
    """
    Check connectivity to external services

    Returns:
        dict: Service name to health status mapping
    """
    services = {}

    # Check PostgreSQL
    try:
        db_url = os.getenv("DATABASE_URL")
        services["postgres"] = bool(db_url) and "postgresql" in db_url
    except Exception:
        services["postgres"] = False

    # Check Redis
    try:
        redis_url = os.getenv("REDIS_URL")
        services["redis"] = bool(redis_url) and "redis" in redis_url
    except Exception:
        services["redis"] = False

    # Check Qdrant
    try:
        qdrant_host = os.getenv("QDRANT_HOST")
        services["qdrant"] = bool(qdrant_host)
    except Exception:
        services["qdrant"] = False

    # Check Ollama
    try:
        ollama_url = os.getenv("OLLAMA_BASE_URL")
        services["ollama"] = bool(ollama_url)
    except Exception:
        services["ollama"] = False

    return services


# Indexing status response model
class IndexingStatusResponse(BaseModel):
    """Indexing status response model"""
    file_monitor: dict
    indexing_queue: dict
    indexer: dict
    database: dict
    timestamp: str


@app.get("/indexing/status", response_model=IndexingStatusResponse, status_code=status.HTTP_200_OK)
async def indexing_status():
    """
    Indexing status endpoint

    Returns comprehensive indexing status including file monitor, queue, and statistics.

    Returns:
        IndexingStatusResponse: Indexing status information
    """
    try:
        from src.indexing.file_monitor import get_monitor_status
        from src.indexing.file_indexer import get_indexer_stats
        from src.indexing.queue import get_queue_status
        from src.indexing.models import get_metadata_stats

        # Get monitor status
        monitor_status = get_monitor_status()

        # Get queue status
        queue_status = get_queue_status()

        # Get indexer stats
        indexer_stats = get_indexer_stats()

        # Get database stats
        try:
            db_stats = await get_metadata_stats()
        except Exception as e:
            logger.warning(f"Could not get database stats: {e}")
            db_stats = {"error": str(e)}

        return IndexingStatusResponse(
            file_monitor={
                "running": monitor_status["running"],
                "monitored_paths": monitor_status["monitored_paths"],
                "ignore_patterns": monitor_status["ignore_patterns"],
                "observer_alive": monitor_status["observer_alive"]
            },
            indexing_queue={
                "processing": queue_status["processing"],
                "queue_size": queue_status["queue_size"],
                "current_item": queue_status["current_item"],
                "stats": queue_status["stats"]
            },
            indexer={
                "total_indexed": indexer_stats["total_indexed"],
                "total_errors": indexer_stats["total_errors"],
                "by_language": indexer_stats["by_language"],
                "supported_languages": indexer_stats["supported_languages"]
            },
            database=db_stats,
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Error getting indexing status: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e), "timestamp": datetime.utcnow().isoformat()}
        )


# Vector status response model
class VectorStatusResponse(BaseModel):
    """Vector status response model"""
    qdrant: dict
    embeddings: dict
    vector_store: dict
    collections: list
    timestamp: str


# Import search models
from src.search.models import SearchRequest, SearchResponse, SearchStats


@app.get("/vector/status", response_model=VectorStatusResponse, status_code=status.HTTP_200_OK)
async def vector_status():
    """
    Vector database status endpoint

    Returns comprehensive vector database status including Qdrant, embeddings, and collections.

    Returns:
        VectorStatusResponse: Vector database status information
    """
    try:
        from src.vector_db.qdrant_client import get_qdrant_status
        from src.vector_db.embeddings import get_embedding_stats
        from src.vector_db.vector_store import get_vector_stats
        from src.vector_db.collections import list_collections, get_collection_stats

        # Get Qdrant status
        qdrant_status = await get_qdrant_status()

        # Get embedding stats
        embedding_stats = get_embedding_stats()

        # Get vector store stats
        vector_stats = get_vector_stats()

        # Get collection information
        collection_names = await list_collections()
        collections_info = []

        for collection_name in collection_names:
            collection_stats = await get_collection_stats(collection_name)
            if collection_stats:
                collections_info.append(collection_stats)

        return VectorStatusResponse(
            qdrant=qdrant_status,
            embeddings=embedding_stats,
            vector_store=vector_stats,
            collections=collections_info,
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        logger.error(f"Error getting vector status: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e), "timestamp": datetime.utcnow().isoformat()}
        )


@app.post("/search/semantic", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def semantic_search(request: SearchRequest):
    """
    Semantic code search endpoint

    Performs natural language search over the indexed codebase using vector embeddings.

    Args:
        request: Search request with query and optional filters

    Returns:
        SearchResponse: Search results with relevance scores
    """
    try:
        from src.search.semantic_search import search_code

        logger.info(f"Semantic search request: '{request.query}'")

        # Perform search
        response = await search_code(request)

        logger.info(f"Search completed: {response.total_results} results in {response.search_time_ms:.2f}ms")
        return response

    except ValueError as e:
        logger.error(f"Validation error in search: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(e), "timestamp": datetime.utcnow().isoformat()}
        )
    except Exception as e:
        logger.error(f"Error during semantic search: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e), "timestamp": datetime.utcnow().isoformat()}
        )


@app.get("/search/stats", response_model=SearchStats, status_code=status.HTTP_200_OK)
async def search_stats():
    """
    Search statistics endpoint

    Returns comprehensive search statistics including performance metrics.

    Returns:
        SearchStats: Search statistics
    """
    try:
        from src.search.semantic_search import get_search_stats

        stats = get_search_stats()
        return stats

    except Exception as e:
        logger.error(f"Error getting search stats: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e), "timestamp": datetime.utcnow().isoformat()}
        )


@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """
    Root endpoint

    Returns basic information about the Context MCP server.
    """
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "description": APP_DESCRIPTION,
        "status": "running",
        "health_endpoint": "/health",
        "docs_endpoint": "/docs"
    }


if __name__ == "__main__":
    import uvicorn

    # Run server
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )
