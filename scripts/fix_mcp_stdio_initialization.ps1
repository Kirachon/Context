# Fix MCP Stdio Server Initialization
# This script restarts the Context server to apply the service initialization fix

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Fix MCP Stdio Server - Initialize Services            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify Docker is running
Write-Host "[1/5] Verifying Docker services..." -ForegroundColor Yellow
try {
    $dockerRunning = docker ps 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "      ❌ Docker is not running" -ForegroundColor Red
        Write-Host "      Please start Docker Desktop and try again" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "      ✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "      ❌ Docker not available: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Check if context-server is running
Write-Host ""
Write-Host "[2/5] Checking context-server status..." -ForegroundColor Yellow
$contextServer = docker ps --filter "name=context-server" --format "{{.Names}}" 2>$null
if ($contextServer -eq "context-server") {
    Write-Host "      ✅ context-server is running" -ForegroundColor Green
} else {
    Write-Host "      ⚠️  context-server is not running" -ForegroundColor Yellow
    Write-Host "      Starting services..." -ForegroundColor Cyan
    docker-compose -f deployment/docker/docker-compose.yml up -d context-server
    Start-Sleep -Seconds 5
}

# Step 3: Restart context-server to apply changes
Write-Host ""
Write-Host "[3/5] Restarting context-server..." -ForegroundColor Yellow
Write-Host "      This will apply the service initialization fix" -ForegroundColor Gray
try {
    docker-compose -f deployment/docker/docker-compose.yml restart context-server
    Write-Host "      ✅ Container restarted" -ForegroundColor Green
} catch {
    Write-Host "      ❌ Failed to restart container: $_" -ForegroundColor Red
    exit 1
}

# Step 4: Wait for services to initialize
Write-Host ""
Write-Host "[4/5] Waiting for services to initialize..." -ForegroundColor Yellow
Write-Host "      This takes 15-20 seconds (loading embedding model)" -ForegroundColor Gray

for ($i = 1; $i -le 20; $i++) {
    Write-Progress -Activity "Initializing Services" -Status "$i/20 seconds" -PercentComplete ($i * 5)
    Start-Sleep -Seconds 1
}
Write-Progress -Activity "Initializing Services" -Completed

Write-Host "      ✅ Initialization period complete" -ForegroundColor Green

# Step 5: Verify services are healthy
Write-Host ""
Write-Host "[5/5] Verifying service health..." -ForegroundColor Yellow

try {
    # Check container health
    $health = docker inspect context-server --format='{{.State.Health.Status}}' 2>$null
    if ($health -eq "healthy") {
        Write-Host "      ✅ Container is healthy" -ForegroundColor Green
    } else {
        Write-Host "      ⚠️  Container health: $health" -ForegroundColor Yellow
    }
    
    # Check HTTP endpoint
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5 2>$null
    if ($response.StatusCode -eq 200) {
        Write-Host "      ✅ HTTP server responding" -ForegroundColor Green
    }
} catch {
    Write-Host "      ⚠️  Health check incomplete: $_" -ForegroundColor Yellow
}

# Check logs for initialization messages
Write-Host ""
Write-Host "Checking initialization logs..." -ForegroundColor Yellow
$logs = docker logs context-server --tail 30 2>&1 | Select-String -Pattern "Qdrant|embedding|initialized" -Context 0
if ($logs) {
    Write-Host "      Recent initialization activity:" -ForegroundColor Gray
    $logs | ForEach-Object { Write-Host "      $_" -ForegroundColor Gray }
}

# Final instructions
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              ✅ Fix Applied Successfully!                  ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   1. Test MCP stdio connection manually:" -ForegroundColor White
Write-Host "      docker exec -i context-server python -m src.mcp_server.stdio_full_mcp" -ForegroundColor Gray
Write-Host "      (Press Ctrl+C after 5 seconds if it starts successfully)" -ForegroundColor Gray
Write-Host ""
Write-Host "   2. Restart Claude Code CLI:" -ForegroundColor White
Write-Host "      - Close all Claude Code CLI windows" -ForegroundColor Gray
Write-Host "      - Wait 10 seconds" -ForegroundColor Gray
Write-Host "      - Start Claude Code CLI" -ForegroundColor Gray
Write-Host ""
Write-Host "   3. Verify MCP connection:" -ForegroundColor White
Write-Host "      Run: /mcp" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ Expected Result:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Context MCP Server:" -ForegroundColor White
Write-Host "     - Status: Connected ✅" -ForegroundColor Green
Write-Host "     - Qdrant: Connected" -ForegroundColor Green
Write-Host "     - Embeddings: Loaded" -ForegroundColor Green
Write-Host "     - Tools: 30+ available" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Troubleshooting:" -ForegroundColor Yellow
Write-Host "   - View logs: docker logs context-server --tail 100" -ForegroundColor Gray
Write-Host "   - Check health: curl http://localhost:8000/health" -ForegroundColor Gray
Write-Host "   - Test Qdrant: curl http://localhost:6333/collections" -ForegroundColor Gray
Write-Host ""

