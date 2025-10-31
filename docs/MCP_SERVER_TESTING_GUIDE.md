# MCP Server Testing Guide

## Overview

This guide provides instructions for testing the Context MCP server implementation, including startup verification, tool endpoint testing, and Claude Code CLI integration.

## Prerequisites

- Docker and Docker Compose installed
- Claude Code CLI installed (for MCP integration testing)
- Access to the Context repository

## Testing Steps

### 1. Start the Development Environment

```bash
cd deployment/docker
docker-compose up -d
```

This starts all services:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Qdrant (port 6333)
- Context Server with MCP (port 8000)

### 2. Verify Server Startup

Check that the MCP server started successfully:

```bash
# View server logs
docker-compose logs -f context-server

# Expected log output:
# - "Initializing MCP Server: Context v0.1.0"
# - "Creating FastMCP server instance"
# - "MCP server started successfully on Context"
# - "Available capabilities: health_check, capabilities, semantic_search"
```

### 3. Test Health Endpoint

Verify the FastAPI health endpoint includes MCP status:

```bash
curl http://localhost:8000/health | jq
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2025-10-31T...",
  "environment": "development",
  "services": {
    "postgres": true,
    "redis": true,
    "qdrant": true,
    "ollama": false
  },
  "mcp_server": {
    "enabled": true,
    "running": true,
    "connection_state": "listening"
  }
}
```

### 4. Run Unit Tests

Execute the test suite inside the Docker container:

```bash
# Run all MCP server tests
docker-compose exec context-server pytest tests/unit/test_mcp_server.py -v

# Run MCP tools tests
docker-compose exec context-server pytest tests/unit/test_mcp_tools.py -v

# Run integration tests
docker-compose exec context-server pytest tests/integration/test_mcp_integration.py -v

# Run all tests with coverage
docker-compose exec context-server pytest tests/ --cov=src/mcp_server --cov-report=html
```

### 5. Test MCP Tool Endpoints

The MCP server exposes 4 tool endpoints that can be invoked via Claude Code CLI:

#### Tool 1: health_check
Returns comprehensive server health status.

#### Tool 2: server_info
Returns basic server metadata and version information.

#### Tool 3: list_capabilities
Lists all available MCP tools and server features.

#### Tool 4: get_configuration
Returns server configuration details (non-sensitive).

### 6. Test with Claude Code CLI

Configure Claude Code CLI to connect to the Context MCP server:

```bash
# Add Context MCP server to Claude Code CLI configuration
# Edit ~/.config/claude/mcp_servers.json

{
  "context": {
    "command": "docker",
    "args": ["exec", "-i", "context-server", "python", "-m", "src.mcp_server.mcp_app"],
    "env": {
      "MCP_ENABLED": "true"
    }
  }
}
```

Then test the connection:

```bash
# Start Claude Code CLI
claude-code

# In Claude Code CLI, invoke MCP tools:
# - "Check the health of the Context server"
# - "List available capabilities"
# - "Get server configuration"
```

### 7. Test Connection Lifecycle

Test connection handling:

```bash
# Monitor logs while connecting/disconnecting
docker-compose logs -f context-server

# Expected log output:
# - "MCP client connected successfully"
# - "Connection state: connected"
# - "MCP client disconnected"
# - "Connection state: disconnected"
```

### 8. Test Graceful Shutdown

Test signal handling and graceful shutdown:

```bash
# Send SIGTERM to the server
docker-compose stop context-server

# Expected log output:
# - "Received SIGTERM signal, initiating graceful shutdown..."
# - "Initiating MCP server shutdown..."
# - "Closing active connections..."
# - "MCP server shutdown completed successfully"

# Restart the server
docker-compose start context-server
```

### 9. Test Error Recovery

Test reconnection logic:

```bash
# Simulate connection error by restarting the server
docker-compose restart context-server

# Monitor logs for reconnection attempts
docker-compose logs -f context-server

# Expected log output:
# - "MCP connection error: ..."
# - "Attempting reconnection after error..."
# - "Reconnection attempt 1/3"
# - "Reconnection successful"
```

### 10. Performance Testing

Test server performance:

```bash
# Run performance tests
docker-compose exec context-server pytest tests/performance/ -v

# Test health endpoint response time
time curl http://localhost:8000/health

# Expected: < 200ms response time
```

## Validation Checklist

- [ ] Server starts successfully with MCP enabled
- [ ] Health endpoint includes MCP status
- [ ] All 4 MCP tools are registered
- [ ] Connection lifecycle events are logged
- [ ] Graceful shutdown works (SIGTERM/SIGINT)
- [ ] Reconnection logic works after errors
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Claude Code CLI can connect and invoke tools
- [ ] Performance meets requirements (< 200ms health check)

## Troubleshooting

### MCP Server Not Starting

Check logs:
```bash
docker-compose logs context-server | grep -i error
```

Common issues:
- Missing dependencies: Rebuild Docker image
- Configuration errors: Check .env file
- Port conflicts: Ensure port 8000 is available

### Connection Failures

Check MCP status:
```bash
curl http://localhost:8000/health | jq '.mcp_server'
```

If `connection_state` is "error" or "failed":
- Check logs for error details
- Verify FastMCP is installed correctly
- Restart the server

### Tool Invocation Failures

Check tool registration:
```bash
docker-compose exec context-server python3 -c "
from src.mcp_server.mcp_app import mcp_server
status = mcp_server.get_status()
print(f'Capabilities: {status[\"capabilities\"]}')
"
```

## Next Steps

After successful testing:
1. Mark story as done in sprint-status.yaml
2. Create PR for code review
3. Deploy to staging environment
4. Perform end-to-end testing with real Claude Code CLI workflows

## References

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Story 1.2 Implementation](../stories/1-2-core-mcp-server-implementation.md)
- [Architecture Decision AD-003](./architecture-Context-2025-10-31.md#AD-003-MCP-Protocol-Integration)

