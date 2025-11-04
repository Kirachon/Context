# Configure MCP Servers for Claude Code CLI
# This script adds the Context MCP server to Claude Code CLI configuration

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        Configure Context MCP Server for Claude Code CLI    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Configuration paths
$configPath = "C:\Users\preda\.claude.json"
$backupPath = "C:\Users\preda\.claude.json.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# Step 1: Verify file exists
Write-Host "[1/6] Verifying configuration file..." -ForegroundColor Yellow
if (-not (Test-Path $configPath)) {
    Write-Host "      ❌ Configuration file not found: $configPath" -ForegroundColor Red
    Write-Host "      Please ensure Claude Code CLI is installed and has been run at least once." -ForegroundColor Yellow
    exit 1
}
Write-Host "      ✅ Configuration file found" -ForegroundColor Green

# Step 2: Backup configuration
Write-Host ""
Write-Host "[2/6] Backing up configuration..." -ForegroundColor Yellow
try {
    Copy-Item $configPath $backupPath -Force
    Write-Host "      ✅ Backup created" -ForegroundColor Green
    Write-Host "      📁 $backupPath" -ForegroundColor Gray
} catch {
    Write-Host "      ❌ Failed to create backup: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Read and parse configuration
Write-Host ""
Write-Host "[3/6] Reading configuration..." -ForegroundColor Yellow
try {
    $config = Get-Content $configPath -Raw | ConvertFrom-Json
    Write-Host "      ✅ Configuration loaded" -ForegroundColor Green
} catch {
    Write-Host "      ❌ Failed to parse JSON: $_" -ForegroundColor Red
    exit 1
}

# Step 4: Add mcpServers property if it doesn't exist
Write-Host ""
Write-Host "[4/6] Configuring MCP servers..." -ForegroundColor Yellow

# Check if mcpServers property exists
if (-not $config.PSObject.Properties['mcpServers']) {
    Write-Host "      → Adding mcpServers property..." -ForegroundColor Cyan
    $config | Add-Member -NotePropertyName 'mcpServers' -NotePropertyValue ([PSCustomObject]@{}) -Force
    Write-Host "      ✅ mcpServers property added" -ForegroundColor Green
}

# Add Context server configuration
Write-Host "      → Adding Context MCP server..." -ForegroundColor Cyan
$contextServer = [PSCustomObject]@{
    type = "stdio"
    command = "docker"
    args = @(
        "exec",
        "-i",
        "context-server",
        "python",
        "-m",
        "src.mcp_server.stdio_full_mcp"
    )
    env = [PSCustomObject]@{
        MCP_ENABLED = "true"
        PYTHONPATH = "/app"
    }
    disabled = $false
    timeout = 30000
    description = "Context MCP Server - Semantic code search and analysis"
}

$config.mcpServers | Add-Member -NotePropertyName 'context' -NotePropertyValue $contextServer -Force
Write-Host "      ✅ Context server configured" -ForegroundColor Green

# Step 5: Save configuration
Write-Host ""
Write-Host "[5/6] Saving configuration..." -ForegroundColor Yellow
try {
    $config | ConvertTo-Json -Depth 10 | Set-Content $configPath -NoNewline
    Write-Host "      ✅ Configuration saved" -ForegroundColor Green
} catch {
    Write-Host "      ❌ Failed to save configuration: $_" -ForegroundColor Red
    Write-Host "      Restoring backup..." -ForegroundColor Yellow
    Copy-Item $backupPath $configPath -Force
    exit 1
}

# Step 6: Verify Docker services
Write-Host ""
Write-Host "[6/6] Verifying Docker services..." -ForegroundColor Yellow
try {
    $contextServer = docker ps --filter "name=context-server" --format "{{.Status}}" 2>$null
    if ($contextServer -match "Up") {
        Write-Host "      ✅ context-server is running" -ForegroundColor Green
    } else {
        Write-Host "      ⚠️  context-server is not running" -ForegroundColor Yellow
        Write-Host "      Start with: docker-compose -f deployment/docker/docker-compose.yml up -d" -ForegroundColor Gray
    }
} catch {
    Write-Host "      ⚠️  Docker not available" -ForegroundColor Yellow
}

# Final instructions
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              ✅ Configuration Complete!                     ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   1. Restart Claude Code CLI completely" -ForegroundColor White
Write-Host "      - Close all Claude Code CLI windows" -ForegroundColor Gray
Write-Host "      - Wait 10 seconds" -ForegroundColor Gray
Write-Host "      - Start Claude Code CLI" -ForegroundColor Gray
Write-Host ""
Write-Host "   2. Verify MCP servers are detected:" -ForegroundColor White
Write-Host "      Run: /mcp" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ Expected Result:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Context MCP Server:" -ForegroundColor White
Write-Host "     - Status: Connected ✅" -ForegroundColor Green
Write-Host "     - Transport: stdio" -ForegroundColor Gray
Write-Host "     - Timeout: 30000ms" -ForegroundColor Gray
Write-Host "     - Tools: 30+ available" -ForegroundColor Gray
Write-Host ""
Write-Host "📁 Backup saved to:" -ForegroundColor Gray
Write-Host "   $backupPath" -ForegroundColor Gray
Write-Host ""

