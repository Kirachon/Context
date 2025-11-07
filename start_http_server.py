#!/usr/bin/env python3
"""
Context MCP HTTP Server Startup Script

Convenient script to start the Context MCP server with HTTP transport.
This provides a persistent server instance that improves reliability
when working with multiple projects in Claude Code CLI.

Usage:
    python start_http_server.py

Or with custom host/port:
    python start_http_server.py --host 0.0.0.0 --port 9000

The server will be available at:
    http://127.0.0.1:8000/ (default)

Update your ~/.claude.json to use HTTP transport:
    {
      "mcpServers": {
        "context": {
          "type": "http",
          "url": "http://localhost:8000/"
        }
      }
    }
"""
import argparse
import sys
import os
import logging

import uvicorn
# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config.settings import settings
from src.logging.manager import configure_logging

# Configure logging
configure_logging(level=settings.log_level, fmt=settings.log_format, use_stderr=False)
logger = logging.getLogger(__name__)


def main():
    """Parse arguments and start the HTTP server"""
    parser = argparse.ArgumentParser(
        description="Start Context MCP HTTP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default settings (localhost:8000)
  python start_http_server.py

  # Start on all interfaces
  python start_http_server.py --host 0.0.0.0

  # Use custom port
  python start_http_server.py --port 9000

  # Enable debug logging
  python start_http_server.py --log-level DEBUG

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
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=settings.log_level,
        help=f"Logging level (default: {settings.log_level})"
    )

    args = parser.parse_args()

    # Update log level if specified
    if args.log_level != settings.log_level:
        configure_logging(level=args.log_level, fmt=settings.log_format, use_stderr=False)

    logger.info("=" * 70)
    logger.info("Context MCP HTTP Server")
    logger.info("=" * 70)
    logger.info(f"Server: {settings.mcp_server_name} v{settings.mcp_server_version}")
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"URL: http://{args.host}:{args.port}/")
    logger.info(f"Log Level: {args.log_level}")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Starting server... Press Ctrl+C to stop")
    logger.info("")

    # Import the HTTP server module
    from src.mcp_server.http_server import create_app

    # Run the server using FastMCP's built-in run() method
    try:
        app = create_app()
        uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level.lower())
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

