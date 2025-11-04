# Claude Code CLI MCP Connection "Shutdown" Issue - Diagnosis & Solution

## 📊 Diagnostic Results

### ✅ What's Working:

1. **Docker Services**: `context-server` container is running and healthy
2. **MCP Server Code**: All tools load and register successfully
3. **Stdio Entry Point**: `src.mcp_server.stdio_full_mcp` works perfectly
4. **Configuration**: `.claude.json` has correct Context server configuration
5. **Manual Test**: `docker exec -i context-server python -m src.mcp_server.stdio_full_mcp` starts successfully

### ❌ The Problem:

**MCP Server Status in Claude Code CLI:**
```
MCP Server:
  - Enabled: ✅
  - Running: ❌
  - Connection State: Shutdown
```

### 🔍 Root Cause:

The MCP server takes **~18 seconds** to fully initialize:
- Loading sentence-transformers embedding model (all-MiniLM-L6-v2)
- Connecting to Qdrant vector database
- Initializing all tool categories

**Claude Code CLI's default MCP connection timeout may be too short**, causing it to give up before the server finishes starting.

---

## 💡 Solution: Increase MCP Connection Timeout

### Option 1: Manual Configuration Edit (RECOMMENDED)

1. **Open the configuration file:**
   ```
   C:\Users\preda\.claude.json
   ```

2. **Find the `context` server configuration** (around line 200):
   ```json
   "context": {
     "type": "stdio",
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
     },
     "disabled": false
   }
   ```

3. **Add a `timeout` field** (in milliseconds):
   ```json
   "context": {
     "type": "stdio",
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
     },
     "disabled": false,
     "timeout": 30000
   }
   ```

4. **Save the file** and **restart Claude Code CLI completely**

---

### Option 2: Set Environment Variable

Set the MCP timeout globally:

```powershell
$env:MCP_TIMEOUT = "30000"
```

Add this to your PowerShell profile to make it permanent:
```powershell
notepad $PROFILE
```

Add this line:
```powershell
$env:MCP_TIMEOUT = "30000"
```

---

## 🧪 Verification Steps

After applying the solution:

1. **Restart Claude Code CLI completely**
   - Close all Claude Code CLI windows
   - Wait 5 seconds
   - Start Claude Code CLI again

2. **Check MCP server status:**
   ```
   /mcp
   ```

3. **Expected result:**
   ```
   MCP Server:
     - Enabled: ✅
     - Running: ✅
     - Connection State: Connected
   ```

4. **Test a Context tool:**
   Try using one of the Context MCP tools to verify the connection works

---

## 📝 Additional Notes

### Why Manual Testing Works But Claude Code CLI Doesn't:

- **Manual test**: We wait patiently for the server to start (no timeout)
- **Claude Code CLI**: Has a default timeout (likely 10-15 seconds) and gives up if the server doesn't respond in time

### Alternative: Optimize Server Startup Time

If increasing the timeout doesn't work, we can optimize the server startup:

1. **Pre-load the embedding model** in the Docker container
2. **Use a smaller/faster embedding model**
3. **Lazy-load components** instead of initializing everything at startup

---

## 🎯 Summary

**The Context MCP server is working perfectly** - it just needs more time to start up. Adding a 30-second timeout to the configuration should resolve the "Shutdown" connection state issue.

**Next Steps:**
1. Edit `.claude.json` to add `"timeout": 30000` to the Context server configuration
2. Restart Claude Code CLI
3. Verify the connection state shows "Connected"

