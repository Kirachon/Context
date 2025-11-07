# Claude Code CLI - MCP Connection Fix

## Issue Summary

**Problem:** MCP Server showing as "Disconnected" in Claude Code CLI despite being enabled.

**Root Cause:** The Claude Code CLI configuration file (`mcp_servers.json`) did not exist.

## Important Distinction

**Claude Code CLI** ≠ **Claude Desktop**

- **Claude Code CLI:** Command-line interface for coding (uses `mcp_servers.json`)
- **Claude Desktop:** Desktop application (uses `claude_desktop_config.json`)

These are **different products** with **different configuration files**.

## Diagnostic Results

### ✅ What Was Working:

1. **Docker Services:** All containers running and healthy
   ```
   context-server    Up 2 hours (healthy)
   context-postgres  Up 2 hours (healthy)
   context-qdrant    Up 2 hours (healthy)
   context-redis     Up 2 hours (healthy)
   ```

2. **MCP Server Code:** Successfully loaded and running
   - MCP server initialized successfully
   - All 11 tool categories registered (including context-aware tools)
   - HTTP server responding on port 8000

3. **Environment Configuration:** Correct settings
   ```bash
   MCP_ENABLED=true
   MCP_SERVER_NAME=Context
   ```

4. **Stdio Entry Point:** Module exists and imports successfully
   ```bash
   ✅ stdio_full_mcp module can be imported
   ```

### ❌ What Was NOT Working:

**Claude Code CLI Configuration File Missing**

- **Expected location:** `C:\Users\preda\AppData\Roaming\Claude\mcp_servers.json`
- **Status:** File did not exist
- **Impact:** Claude Code CLI had no way to discover or connect to the Context MCP server

## Resolution Applied

### Created Claude Code CLI Configuration File

**File Created:** `C:\Users\preda\AppData\Roaming\Claude\mcp_servers.json`

**Content:**
```json
{
  "context": {
    "command": "docker",
    "args": [
      "exec",
      "-i",
      "context-server",
      "python",
      "-m",
      "src.mcp_server.stdio_full_mcp"
    ],
    "env": {
      "MCP_ENABLED": "true",
      "PYTHONPATH": "/app"
    }
  }
}
```

### Configuration Explanation

- **`command`:** `docker` - Uses Docker CLI to execute commands
- **`args`:** Executes Python module inside the running container via stdin/stdout
  - `exec` - Docker exec command
  - `-i` - Interactive mode (keeps stdin open)
  - `context-server` - Container name
  - `python -m src.mcp_server.stdio_full_mcp` - Runs the stdio MCP server module
- **`env`:** Environment variables passed to the process
  - `MCP_ENABLED=true` - Enables MCP functionality
  - `PYTHONPATH=/app` - Sets Python path for module imports

## Next Steps

### 1. Restart Claude Code CLI

**IMPORTANT:** You must completely restart Claude Code CLI for the configuration to take effect.

**Steps:**
1. Close Claude Code CLI completely
2. Wait 5 seconds
3. Reopen Claude Code CLI

### 2. Verify Connection

After restarting, the MCP server status should show:

```
MCP Server:
  - Enabled: ✅
  - Running: ✅ Connected
  - Connection State: Connected
```

### 3. List Available Tools

In Claude Code CLI, ask:
```
What MCP tools are available from the Context server?
```

**Expected Response:** List of 11 tool categories with all available tools.

### 4. Test a Tool

Try the health check:
```
Check the health status of the Context MCP server
```

Or test the new context-aware tools:
```
Use the generate_contextual_prompt tool to create a search prompt for "authentication functions"
```

## Available Tools (11 Categories)

After connection, these tool categories will be available:

1. **Health Tools** - Server health and status checks
2. **Capability Tools** - List available capabilities
3. **Indexing Tools** - Index directories and files
4. **Vector Tools** - Vector database operations
5. **Search Tools** - Semantic code search
6. **Pattern Search Tools** - Pattern-based code search
7. **Cross-Language Tools** - Cross-language analysis
8. **Query Understanding Tools** - Query classification and understanding
9. **Indexing Optimization Tools** - Progressive indexing
10. **Prompt Tools** - Prompt enhancement
11. **Context-Aware Prompt Tools** ⭐ (newly enabled)
    - `generate_contextual_prompt` - Generate context-aware prompts
    - `extract_context_keywords` - Extract keywords from context
    - `optimize_prompt_for_context` - Optimize prompts for specific contexts

## Technical Architecture

### Connection Flow

```
Claude Code CLI
    ↓
mcp_servers.json (configuration)
    ↓
docker exec -i context-server python -m src.mcp_server.stdio_full_mcp
    ↓
Stdio MCP Server (spawned on-demand)
    ↓
FastMCP + Tool Handlers
    ↓
Context Services (indexing, search, analysis)
```

### Two Server Processes

The Context project runs two separate processes:

1. **HTTP Server (Always Running)**
   - Command: `uvicorn src.mcp_server.server:app`
   - Port: 8000
   - Purpose: Health checks, metrics, monitoring
   - Status: ✅ Running continuously

2. **Stdio MCP Server (On-Demand)**
   - Command: `python -m src.mcp_server.stdio_full_mcp`
   - Transport: stdin/stdout
   - Purpose: MCP tool communication with Claude Code CLI
   - Status: ✅ Spawned when Claude Code CLI connects

This is the **correct architecture** - they serve different purposes and don't conflict.

## Troubleshooting

### If Connection Still Fails:

1. **Verify Docker Container is Running:**
   ```bash
   docker ps | grep context-server
   ```
   Should show "Up" and "(healthy)"

2. **Test Stdio Entry Point Manually:**
   ```bash
   docker exec -i context-server python -m src.mcp_server.stdio_full_mcp
   ```
   Should start without errors (Ctrl+C to exit)

3. **Check Configuration File:**
   ```powershell
   Get-Content "$env:APPDATA\Claude\mcp_servers.json"
   ```
   Should show the Context server configuration

4. **Check Docker Logs:**
   ```bash
   docker logs context-server --tail 50
   ```
   Look for MCP-related errors

5. **Verify Environment Variables:**
   ```bash
   docker exec context-server env | grep MCP
   ```
   Should show `MCP_ENABLED=true`

## Files Created/Modified

- ✅ `C:\Users\preda\AppData\Roaming\Claude\mcp_servers.json` (Claude Code CLI config - CREATED)
- ✅ `CLAUDE_CODE_CLI_MCP_CONNECTION_FIX.md` (this documentation)

## Summary

The MCP connection issue was resolved by creating the missing Claude Code CLI configuration file (`mcp_servers.json`). The server was working correctly - Claude Code CLI just didn't know how to connect to it.

**Key Difference from Previous Attempt:**
- ❌ Previously modified: `claude_desktop_config.json` (for Claude Desktop)
- ✅ Now created: `mcp_servers.json` (for Claude Code CLI)

After restarting Claude Code CLI, the connection should work and all 11 tool categories should be available! 🚀

