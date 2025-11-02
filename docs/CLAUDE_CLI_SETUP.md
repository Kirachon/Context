# Claude Code CLI Setup for Context MCP Server

This guide explains how to configure Claude Code CLI to use the Context MCP server for semantic code search and context-aware prompt enhancement.

## Prerequisites

- Docker and Docker Compose installed
- Context server running in Docker
- Claude Code CLI installed

## Step 1: Verify Docker Services

Ensure all services are running:

```bash
cd deployment/docker
docker-compose ps
```

You should see these services running:
- `postgres` - Database
- `redis` - Cache
- `qdrant` - Vector database
- `ollama` - LLM inference
- `context-server` - Main application

If not running, start them:

```bash
docker-compose up -d
```

## Step 2: Configure Claude Code CLI

### Linux/Mac

Create or edit `~/.config/claude/mcp_servers.json`:

```json
{
  "context": {
    "command": "docker",
    "args": ["exec", "-i", "context-server", "python", "-m", "src.mcp_server.mcp_app"],
    "env": {
      "MCP_ENABLED": "true",
      "PYTHONPATH": "/app"
    }
  }
}
```

### Windows

Create or edit `%APPDATA%\Claude\mcp_servers.json`:

```json
{
  "context": {
    "command": "docker",
    "args": ["exec", "-i", "context-server", "python", "-m", "src.mcp_server.mcp_app"],
    "env": {
      "MCP_ENABLED": "true",
      "PYTHONPATH": "/app"
    }
  }
}
```

## Step 3: Restart Claude Code CLI

Close and restart Claude Code CLI to pick up the new MCP server configuration.

## Step 4: Verify Connection

In Claude Code CLI, ask:

```
Can you check the health of the Context MCP server?
```

Claude should respond with health status information from the `health_check` tool.

## Step 5: Test Core Functionality

### Index a Directory

```
Please index the /workspace/src directory using the Context server.
```

Claude will call the `index_directory` tool.

### Search Your Codebase

```
Search for authentication functions in the codebase.
```

Claude will call the `semantic_search` tool with your query.

### Check Indexing Status

```
What's the current indexing status?
```

Claude will call the `indexing_status` tool.

### Enhance a Prompt

```
Enhance this prompt with context: "Explain how the authentication system works"
```

Claude will call the `prompt_enhance` tool.

## Available MCP Tools

The Context MCP server provides these tools to Claude:

### Core Tools
- `health_check` - Check server health and status
- `list_capabilities` - List all available tools
- `server_info` - Get server metadata

### Indexing Tools
- `index_directory` - Index a directory of code files
- `indexing_status` - Get current indexing status
- `start_monitoring` - Start file system monitoring
- `stop_monitoring` - Stop file system monitoring

### Search Tools
- `semantic_search` - Search codebase with natural language
- `ast_semantic_search` - Advanced search over code structure
- `search_symbols` - Search for functions, classes, etc.
- `search_classes` - Search for class definitions
- `search_imports` - Search for import statements

### Analysis Tools
- `analyze_codebase_architecture` - Analyze design patterns and architecture
- `find_similar_code` - Find similar code across languages
- `detect_patterns` - Detect design patterns in code

### Prompt Tools
- `prompt_enhance` - Enhance prompts with code context
- `query_classify` - Classify query intent

### Optimization Tools
- `progressive_index_start` - Start progressive indexing
- `progressive_index_status` - Check indexing progress
- `progressive_index_add_files` - Add files to indexing queue

## Troubleshooting

### Claude doesn't see the Context server

1. Check that Docker services are running: `docker-compose ps`
2. Verify the MCP server is enabled in `.env`: `MCP_ENABLED=true`
3. Check Claude CLI logs for connection errors
4. Restart Claude Code CLI

### Indexing fails

1. Check Docker logs: `docker logs context-server`
2. Verify the directory path is accessible from inside the container
3. Check disk space and memory

### Search returns no results

1. Ensure the codebase has been indexed first
2. Check indexing status with `indexing_status` tool
3. Try a broader search query

## Configuration

The Context server is configured for personal use with these settings in `deployment/docker/.env`:

```bash
# Disabled for simplicity
API_AUTH_ENABLED=false
RATE_LIMIT_ENABLED=false
CONVERSATION_STATE_ENABLED=false

# MCP enabled
MCP_ENABLED=true
```

## Next Steps

- Index your main codebase
- Try semantic searches with natural language
- Use prompt enhancement for better code explanations
- Explore cross-language analysis tools
- Set up file monitoring for automatic re-indexing

## Support

For issues or questions:
- Check Docker logs: `docker logs context-server`
- Review the main README.md
- Check the technical specification in `docs/tech-spec-Context-2025-10-31.md`

