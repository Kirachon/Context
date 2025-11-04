# MCP Connection Fix Script - Simple and Reliable
# This script adds timeout to Context MCP server configuration

param(
    [Parameter(Mandatory=$false)]
    [int]$TimeoutMs = 30000
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     MCP Connection Fix - Add Timeout Configuration         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Configuration paths
$configPath = "$env:APPDATA\Claude\.claude.json"
$backupPath = "$env:APPDATA\Claude\.claude.json.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# Step 1: Backup configuration
Write-Host "[1/6] Backing up configuration..." -ForegroundColor Yellow
try {
    if (Test-Path $configPath) {
        Copy-Item $configPath $backupPath -Force
        Write-Host "      ✅ Backup created" -ForegroundColor Green
        Write-Host "      📁 $backupPath" -ForegroundColor Gray
    } else {
        Write-Host "      ❌ Configuration file not found: $configPath" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "      ❌ Failed to create backup: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Read configuration
Write-Host ""
Write-Host "[2/6] Reading configuration..." -ForegroundColor Yellow
try {
    $jsonContent = Get-Content $configPath -Raw
    Write-Host "      ✅ Configuration loaded ($($jsonContent.Length) bytes)" -ForegroundColor Green
} catch {
    Write-Host "      ❌ Failed to read configuration: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Check if timeout already exists
Write-Host ""
Write-Host "[3/6] Checking current configuration..." -ForegroundColor Yellow
if ($jsonContent -match '"context":[^}]*"timeout":\s*\d+') {
    Write-Host "      ⚠️  Timeout already configured" -ForegroundColor Yellow
    Write-Host "      Current value: $($matches[0] -replace '.*"timeout":\s*(\d+).*', '$1') ms" -ForegroundColor Gray
    Write-Host ""
    $response = Read-Host "      Update timeout to $TimeoutMs ms? (y/n)"
    if ($response -ne 'y') {
        Write-Host "      Operation cancelled" -ForegroundColor Gray
        exit 0
    }
    # Remove existing timeout
    $jsonContent = $jsonContent -replace '(,\s*"timeout":\s*\d+)', ''
}

# Step 4: Add timeout parameter
Write-Host ""
Write-Host "[4/6] Adding timeout parameter ($TimeoutMs ms)..." -ForegroundColor Yellow

# Find the context server configuration and add timeout
# Pattern: Find "disabled": false within context block and add timeout after it
$pattern = '("context":\s*\{(?:[^{}]|\{[^{}]*\})*"disabled":\s*false)'
if ($jsonContent -match $pattern) {
    $replacement = $matches[1] + ",`n    `"timeout`": $TimeoutMs"
    $jsonContent = $jsonContent -replace $pattern, $replacement
    Write-Host "      ✅ Timeout parameter added" -ForegroundColor Green
} else {
    Write-Host "      ❌ Could not find context server configuration" -ForegroundColor Red
    Write-Host "      Please add manually: `"timeout`": $TimeoutMs" -ForegroundColor Yellow
    exit 1
}

# Step 5: Validate JSON
Write-Host ""
Write-Host "[5/6] Validating JSON syntax..." -ForegroundColor Yellow
try {
    $null = $jsonContent | ConvertFrom-Json
    Write-Host "      ✅ JSON is valid" -ForegroundColor Green
} catch {
    Write-Host "      ❌ JSON validation failed: $_" -ForegroundColor Red
    Write-Host "      Restoring backup..." -ForegroundColor Yellow
    Copy-Item $backupPath $configPath -Force
    Write-Host "      ✅ Backup restored" -ForegroundColor Green
    exit 1
}

# Step 6: Save configuration
Write-Host ""
Write-Host "[6/6] Saving configuration..." -ForegroundColor Yellow
try {
    $jsonContent | Set-Content $configPath -NoNewline
    Write-Host "      ✅ Configuration saved successfully" -ForegroundColor Green
} catch {
    Write-Host "      ❌ Failed to save configuration: $_" -ForegroundColor Red
    Write-Host "      Restoring backup..." -ForegroundColor Yellow
    Copy-Item $backupPath $configPath -Force
    exit 1
}

# Verify Docker services
Write-Host ""
Write-Host "Verifying Docker services..." -ForegroundColor Yellow
try {
    $contextServer = docker ps --filter "name=context-server" --format "{{.Status}}" 2>$null
    if ($contextServer -match "Up") {
        Write-Host "      ✅ context-server is running" -ForegroundColor Green
    } else {
        Write-Host "      ⚠️  context-server is not running" -ForegroundColor Yellow
        Write-Host "      Run: docker-compose -f deployment/docker/docker-compose.yml up -d" -ForegroundColor Gray
    }
} catch {
    Write-Host "      ⚠️  Docker not available or not running" -ForegroundColor Yellow
}

# Final instructions
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              ✅ Fix Applied Successfully!                  ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   1. Close all Claude Code CLI windows" -ForegroundColor White
Write-Host "   2. Wait 10 seconds" -ForegroundColor White
Write-Host "   3. Start Claude Code CLI" -ForegroundColor White
Write-Host "   4. Run '/mcp' to verify connection" -ForegroundColor White
Write-Host ""
Write-Host "✅ Expected Result:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Context MCP Server:" -ForegroundColor White
Write-Host "     - Status: Connected ✅" -ForegroundColor Green
Write-Host "     - Transport: stdio" -ForegroundColor Gray
Write-Host "     - Tools: 30+ available" -ForegroundColor Gray
Write-Host ""
Write-Host "📁 Backup saved to:" -ForegroundColor Gray
Write-Host "   $backupPath" -ForegroundColor Gray
Write-Host ""
Write-Host "💡 If connection still fails:" -ForegroundColor Yellow
Write-Host "   - Check Docker: docker ps | grep context-server" -ForegroundColor Gray
Write-Host "   - View logs: docker logs context-server --tail 50" -ForegroundColor Gray
Write-Host "   - Test manual: docker exec -i context-server python -m src.mcp_server.stdio_full_mcp" -ForegroundColor Gray
Write-Host ""

