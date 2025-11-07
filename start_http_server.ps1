# Context MCP HTTP Server Startup Script (PowerShell)
#
# Convenient script to start the Context MCP server with HTTP transport on Windows.
# This provides a persistent server instance that improves reliability
# when working with multiple projects in Claude Code CLI.
#
# Usage:
#   .\start_http_server.ps1
#
# Or with custom host/port:
#   .\start_http_server.ps1 -Host "0.0.0.0" -Port 9000
#
# The server will be available at:
#   http://127.0.0.1:8000/mcp (default)
#
# Update your ~/.claude.json to use HTTP transport:
#   {
#     "mcpServers": {
#       "context": {
#         "type": "http",
#         "url": "http://localhost:8000/mcp"
#       }
#     }
#   }

param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000,
    [ValidateSet("DEBUG", "INFO", "WARNING", "ERROR")]
    [string]$LogLevel = "INFO",
    [int]$Workers = 1
)

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Change to script directory
Set-Location $ScriptDir

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "Context MCP HTTP Server" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "Host:     " -NoNewline -ForegroundColor Yellow
Write-Host $Host
Write-Host "Port:     " -NoNewline -ForegroundColor Yellow
Write-Host $Port
Write-Host "URL:      " -NoNewline -ForegroundColor Yellow
Write-Host "http://$Host`:$Port/mcp" -ForegroundColor Cyan
Write-Host "Log Level:" -NoNewline -ForegroundColor Yellow
Write-Host " $LogLevel"
Write-Host "Workers:  " -NoNewline -ForegroundColor Yellow
Write-Host $Workers
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting server... Press Ctrl+C to stop" -ForegroundColor Green
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python: $pythonVersion" -ForegroundColor Gray
} catch {
    Write-Host "ERROR: Python not found in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.11+ and add it to your PATH" -ForegroundColor Red
    exit 1
}

# Check if uvicorn is installed
try {
    python -c "import uvicorn" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: uvicorn not installed" -ForegroundColor Red
        Write-Host "Please install it with: pip install uvicorn" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "ERROR: Failed to check for uvicorn" -ForegroundColor Red
    exit 1
}

# Start the server
try {
    if ($Workers -gt 1) {
        python -m uvicorn src.mcp_server.http_server:app `
            --host $Host `
            --port $Port `
            --log-level $LogLevel.ToLower() `
            --workers $Workers
    } else {
        python -m uvicorn src.mcp_server.http_server:app `
            --host $Host `
            --port $Port `
            --log-level $LogLevel.ToLower()
    }
} catch {
    Write-Host ""
    Write-Host "Server stopped" -ForegroundColor Yellow
}

