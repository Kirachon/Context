# Docker Compose Auto-Start Setup - Complete ✅

## 🎉 What Was Done

I've configured your Context MCP HTTP Server to run persistently in Docker with auto-start capabilities. Here's what was set up:

### Files Created/Modified

1. **`deployment/docker/docker-compose.yml`** - Updated
   - Changed command to use new MCP HTTP server: `python -m src.mcp_server.http_server`
   - Added `restart: unless-stopped` to all services for auto-restart
   - Made PostgreSQL optional (vector-only mode works without it)
   - Added workspace volume mount for indexing
   - Updated healthcheck to test MCP initialize handshake

2. **`deployment/docker/docker-compose.minimal.yml`** - Created
   - Minimal configuration with only essential services (Qdrant + Context Server)
   - Perfect for Claude Code CLI integration
   - Faster startup, less resource usage

3. **`DOCKER_COMPOSE_AUTO_START_GUIDE.md`** - Created
   - Complete step-by-step setup instructions
   - Troubleshooting guide
   - Docker Desktop auto-start configuration

4. **`start_docker_mcp_server.ps1`** - Created
   - PowerShell script to automate Docker operations
   - Start/Stop/Restart/Logs/Status commands
   - Automatic health checks

5. **`DOCKER_QUICK_REFERENCE.md`** - Created
   - Quick reference card for common commands
   - Troubleshooting tips
   - Configuration locations

6. **`src/mcp_server/http_server.py`** - Modified
   - Bind address changed to listen on all interfaces inside the container
   - Before:

     ```python
     uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
     ```

   - After:

     ```python
     uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
     ```

   - Why: When running in Docker, binding to `127.0.0.1` only accepts loopback connections from inside the container. The host's traffic arrives via the Docker bridge network, so the server must bind to `0.0.0.0` to accept external connections. This resolves the "Failed to connect" issue in Claude Code CLI.
   - Verification from host (requires both Accept types per MCP spec):

     ```powershell
     $handler = New-Object System.Net.Http.HttpClientHandler
     $client = New-Object System.Net.Http.HttpClient($handler)
     $client.DefaultRequestHeaders.Accept.Clear()
     [void]$client.DefaultRequestHeaders.Accept.ParseAdd('application/json')
     [void]$client.DefaultRequestHeaders.Accept.ParseAdd('text/event-stream')
     $body = '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"host-test","version":"1.0"}}}'
     $content = New-Object System.Net.Http.StringContent($body, [System.Text.Encoding]::UTF8, 'application/json')
     $response = $client.PostAsync('http://127.0.0.1:8000/', $content).Result
     Write-Host ("Status: " + [int]$response.StatusCode)
     ($response.Headers.GetValues('Mcp-Session-Id') | Select-Object -First 1)
     ```

---

## 🚀 Quick Start (3 Steps)

### Step 1: Stop Local Server

```powershell
# Stop your currently running local server (PID 30524)
Stop-Process -Id 30524 -Force
```

### Step 2: Start Docker Server

```powershell
# Navigate to project root
cd D:\GitProjects\Context

# Start the server (minimal setup)
.\start_docker_mcp_server.ps1
```

This will:
- ✅ Build Docker images (first time only, ~5-10 minutes)
- ✅ Start Qdrant vector database
- ✅ Start Context MCP HTTP Server
- ✅ Wait for services to be healthy
- ✅ Show status and next steps

### Step 3: Verify Connection

```powershell
# Test MCP connection
python verify_mcp_http.py

# Expected output:
# ✅ MCP initialize handshake successful
# Session ID: <session-id>
# Server: Context v0.1.0
```

---

## 🔧 Configure Auto-Start on Windows Boot

### Enable Docker Desktop Auto-Start

1. Open **Docker Desktop**
2. Click **Settings** (gear icon)
3. Go to **General** tab
4. Enable:
   - ✅ **Start Docker Desktop when you log in**
5. Click **Apply & Restart**

**That's it!** Your containers are already configured with `restart: unless-stopped`, so they will:
- ✅ Auto-start when Docker Desktop starts
- ✅ Auto-restart if they crash
- ✅ Stay stopped if you manually stop them

---

## 🔌 Claude Code CLI Configuration

**No changes needed!** Your existing configuration already works:

**File**: `C:\Users\<username>\.claude.json`

```json
{
  "mcpServers": {
    "context": {
      "type": "http",
      "url": "http://127.0.0.1:8000/"
    }
  }
}
```

The Docker container publishes port 8000 to `127.0.0.1` on the host, and uvicorn now binds to `0.0.0.0` inside the container so the host can connect; Claude CLI connects seamlessly.

---

## ✅ Verification Checklist

After setup, verify everything is working:

### 1. Check Docker Containers
```powershell
docker ps --filter "name=context"
```

**Expected output:**
```
CONTAINER ID   IMAGE              STATUS                    PORTS                    NAMES
<id>           context-server     Up X seconds (healthy)    0.0.0.0:8000->8000/tcp   context-server
<id>           qdrant/qdrant      Up X seconds (healthy)    0.0.0.0:6333->6333/tcp   context-qdrant
```

### 2. Test MCP Connection
```powershell
python verify_mcp_http.py
```

**Expected output:**
```
✅ MCP initialize handshake successful
Session ID: <session-id>
Protocol Version: 2025-03-26
Server: Context v0.1.0
```

### 3. Test Claude CLI Connection
```powershell
# Restart Claude Code CLI
# Then run:
claude mcp list
```

**Expected output:**
```
✓ context — Connected
```

### 4. Test MCP Tools
In Claude Code CLI, ask:
```
Can you check the indexing status of the Context MCP server?
```

---

## 📊 Common Commands

### Using PowerShell Script (Recommended)

```powershell
# Start server
.\start_docker_mcp_server.ps1

# Stop server
.\start_docker_mcp_server.ps1 -Stop

# Restart server
.\start_docker_mcp_server.ps1 -Restart

# View logs
.\start_docker_mcp_server.ps1 -Logs

# Check status
.\start_docker_mcp_server.ps1 -Status

# Start with all services (PostgreSQL, Redis, monitoring)
.\start_docker_mcp_server.ps1 -Full
```

### Using Docker Compose Directly

```powershell
cd deployment\docker

# Start minimal setup
docker-compose -f docker-compose.minimal.yml up -d

# Stop
docker-compose -f docker-compose.minimal.yml stop

# View logs
docker logs context-server -f

# Restart
docker-compose -f docker-compose.minimal.yml restart
```

---

## 🔄 Switching Between Local and Docker

### Currently Using: Docker (Recommended)
- ✅ Auto-starts with Docker Desktop
- ✅ Persistent, always available
- ✅ Isolated environment
- ✅ Easy to manage

### To Switch Back to Local:
1. Stop Docker: `.\start_docker_mcp_server.ps1 -Stop`
2. Start local: `python -m src.mcp_server.http_server`
3. No config changes needed (both use port 8000)

---

## 🐛 Troubleshooting

### Port 8000 Already in Use
```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Stop the process
Stop-Process -Id <PID> -Force
```

### Container Won't Start
```powershell
# Check logs
docker logs context-server --tail 50

# Common issues:
# - Port 8000 in use (stop local server)
# - Invalid GOOGLE_API_KEY in .env
# - Docker Desktop not running
```

### Container Keeps Restarting
```powershell
# View detailed logs
docker logs context-server --tail 100

# Check Qdrant is healthy
docker ps | grep qdrant
```

### Can't Connect from Claude CLI
```powershell
# 1. Verify container is healthy
docker ps

# 2. Test MCP endpoint
python verify_mcp_http.py

# 3. Restart Claude CLI

# 4. Check .claude.json configuration
cat C:\Users\<username>\.claude.json
```

---

## 📚 Documentation

- **Full Setup Guide**: `DOCKER_COMPOSE_AUTO_START_GUIDE.md`
- **Quick Reference**: `DOCKER_QUICK_REFERENCE.md`
- **Docker Compose Files**:
  - Minimal: `deployment/docker/docker-compose.minimal.yml`
  - Full: `deployment/docker/docker-compose.yml`
- **Environment Config**: `deployment/docker/.env`

---

## 🎯 Success Criteria

You'll know everything is working when:

1. ✅ `docker ps` shows both containers as "healthy"
2. ✅ `python verify_mcp_http.py` returns HTTP 200 with session ID
3. ✅ `claude mcp list` shows "✓ context — Connected"
4. ✅ Claude CLI can use Context MCP tools successfully
5. ✅ Containers auto-start when you reboot Windows and open Docker Desktop
6. ✅ Server is accessible at http://127.0.0.1:8000/

---

## 🎉 What You Get

### Before (Local Server)
- ❌ Manual startup required every time
- ❌ Stops when terminal closes
- ❌ No auto-restart on crash
- ❌ Requires remembering to start it

### After (Docker Server)
- ✅ Auto-starts with Docker Desktop
- ✅ Runs persistently in background
- ✅ Auto-restarts on crash
- ✅ Always available when you need it
- ✅ Isolated environment
- ✅ Easy to manage with scripts

---

## 🚀 Next Steps

1. **Start the server**: `.\start_docker_mcp_server.ps1`
2. **Configure Docker Desktop**: Enable "Start Docker Desktop when you log in"
3. **Test connection**: `python verify_mcp_http.py`
4. **Restart Claude CLI**: Connect and test MCP tools
5. **Enjoy**: Your MCP server is now always available!

---

## 🆘 Need Help?

If you encounter issues:
1. Check container logs: `docker logs context-server`
2. Verify .env configuration: `cat deployment/docker/.env`
3. Test MCP endpoint: `python verify_mcp_http.py`
4. Check Docker Desktop is running
5. Ensure port 8000 is available

For detailed troubleshooting, see `DOCKER_COMPOSE_AUTO_START_GUIDE.md`.

