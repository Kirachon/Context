# Quick Fix Guide - MCP Connection Issue

## 🚨 Problem
Claude Code CLI cannot connect to Context MCP server.

## ✅ Solution (2 Minutes)

### Step 1: Update Claude CLI Config

**Linux/Mac:** Edit `~/.config/claude/mcp_servers.json`  
**Windows:** Edit `%APPDATA%\Claude\mcp_servers.json`

**Change this line:**
```json
"args": ["exec", "-i", "context-server", "python", "-m", "src.mcp_server.mcp_app"],
```

**To this:**
```json
"args": ["exec", "-i", "context-server", "python", "-m", "src.mcp_server.stdio_full_mcp"],
```

**Complete config should look like:**
```json
{
  "context": {
    "command": "docker",
    "args": ["exec", "-i", "context-server", "python", "-m", "src.mcp_server.stdio_full_mcp"],
    "env": {
      "MCP_ENABLED": "true",
      "PYTHONPATH": "/app"
    }
  }
}
```

### Step 2: Restart Claude CLI

1. Close Claude Code CLI completely
2. Wait 5 seconds
3. Reopen Claude Code CLI

### Step 3: Test

Ask Claude:
```
Can you check the health of the Context MCP server?
```

**Expected:** Claude successfully returns server health status ✅

## 🔍 Verify Docker is Running

```bash
cd deployment/docker
docker-compose ps
```

All services should show "Up (healthy)". If not:
```bash
docker-compose up -d
```

## 📋 What Changed?

- **Old entry point:** `src.mcp_server.mcp_app` (uses async/await, doesn't work with stdio)
- **New entry point:** `src.mcp_server.stdio_full_mcp` (proper stdio transport)

## 🆘 Still Not Working?

### Check Docker Logs
```bash
docker logs context-server | tail -20
```

Look for: "Starting FULL STDIO MCP server (all tools)..."

### Verify MCP is Enabled
```bash
docker exec context-server env | grep MCP_ENABLED
```

Should return: `MCP_ENABLED=true`

### Restart Docker Services
```bash
cd deployment/docker
docker-compose restart context-server
```

## 📚 More Information

- **Detailed Fix:** See `docs/MCP_CONNECTION_FIX.md`
- **Full Setup Guide:** See `docs/CLAUDE_CLI_SETUP.md`
- **Testing Guide:** See `docs/MCP_SERVER_TESTING_GUIDE.md`
- **Implementation Summary:** See `MCP_FIX_IMPLEMENTATION_SUMMARY.md`

## ✨ After Connection Works

Try these commands in Claude CLI:

1. **List available tools:**
   ```
   What MCP tools are available from Context?
   ```

2. **Index your codebase:**
   ```
   Please index the /workspace/src directory.
   ```

3. **Search your code:**
   ```
   Search for authentication functions in the codebase.
   ```

4. **Check indexing status:**
   ```
   What's the current indexing status?
   ```

---

**Need help?** Check the troubleshooting section in `MCP_FIX_IMPLEMENTATION_SUMMARY.md`

