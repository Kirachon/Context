#!/usr/bin/env pwsh
# Complete MCP Server Fix - All-in-One Solution
# This script performs all necessary steps to get the Context MCP server fully operational

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Context MCP Server - Complete Fix & Setup Script        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Continue"
$projectRoot = "D:\GitProjects\Context"
Set-Location $projectRoot

# Track overall success
$allStepsSuccessful = $true

# ============================================================================
# STEP 1: Verify Docker is Running
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "STEP 1: Verifying Docker Environment" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

try {
    $dockerVersion = docker --version 2>&1
    Write-Host "✅ Docker is running: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running or not installed" -ForegroundColor Red
    Write-Host "   Please start Docker Desktop and try again" -ForegroundColor Gray
    $allStepsSuccessful = $false
    exit 1
}

# ============================================================================
# STEP 2: Download Embedding Model
# ============================================================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "STEP 2: Downloading Embedding Model" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

Write-Host "Checking if model is already cached..." -ForegroundColor Cyan
$cacheDir = "$env:USERPROFILE\.cache\huggingface"
$modelCached = $false

if (Test-Path $cacheDir) {
    $modelFiles = Get-ChildItem -Path $cacheDir -Recurse -Filter "*all-MiniLM-L6-v2*" -ErrorAction SilentlyContinue
    if ($modelFiles) {
        Write-Host "✅ Model already cached at: $cacheDir" -ForegroundColor Green
        $modelCached = $true
    }
}

if (-not $modelCached) {
    Write-Host "⚠️  Model not found in cache. Downloading..." -ForegroundColor Yellow
    Write-Host "   This will take 5-10 minutes..." -ForegroundColor Gray
    
    # Run the download script
    & "$projectRoot\scripts\download_embedding_model.ps1"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Model download failed" -ForegroundColor Red
        $allStepsSuccessful = $false
    } else {
        Write-Host "✅ Model downloaded successfully" -ForegroundColor Green
    }
}

# ============================================================================
# STEP 3: Verify Docker Compose Configuration
# ============================================================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "STEP 3: Verifying Docker Compose Configuration" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$dockerComposePath = "$projectRoot\deployment\docker\docker-compose.yml"
$dockerComposeContent = Get-Content $dockerComposePath -Raw

if ($dockerComposeContent -like "*/.cache/huggingface*") {
    Write-Host "✅ docker-compose.yml configured with model cache mount" -ForegroundColor Green
} else {
    Write-Host "⚠️  docker-compose.yml missing model cache mount" -ForegroundColor Yellow
    Write-Host "   The configuration should have been updated automatically" -ForegroundColor Gray
    $allStepsSuccessful = $false
}

# ============================================================================
# STEP 4: Restart Context Server Container
# ============================================================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "STEP 4: Restarting Context Server" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

Write-Host "Restarting context-server container..." -ForegroundColor Cyan
docker-compose -f deployment/docker/docker-compose.yml restart context-server

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to restart container" -ForegroundColor Red
    $allStepsSuccessful = $false
} else {
    Write-Host "✅ Container restarted successfully" -ForegroundColor Green
    Write-Host "   Waiting 30 seconds for initialization..." -ForegroundColor Gray
    Start-Sleep -Seconds 30
}

# ============================================================================
# STEP 5: Verify Services Initialized
# ============================================================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "STEP 5: Verifying Service Initialization" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

Write-Host "Checking container logs for initialization messages..." -ForegroundColor Cyan
$logs = docker logs context-server --tail 100 2>&1

# Check for Qdrant connection
if ($logs -like "*Successfully connected to Qdrant*" -or $logs -like "*Qdrant connection initialized*") {
    Write-Host "✅ Qdrant connection successful" -ForegroundColor Green
} else {
    Write-Host "⚠️  Qdrant connection status unclear" -ForegroundColor Yellow
    $allStepsSuccessful = $false
}

# Check for embedding model loading
if ($logs -like "*Embedding service initialized*" -or $logs -like "*EmbeddingService initialized*") {
    Write-Host "✅ Embedding model loaded successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Embedding model failed to load" -ForegroundColor Red
    Write-Host "   Checking for SSL errors..." -ForegroundColor Gray
    
    if ($logs -like "*SSL*" -or $logs -like "*SSLError*") {
        Write-Host "   ⚠️  SSL errors detected - model may still be downloading" -ForegroundColor Yellow
        Write-Host "   Check logs: docker logs context-server --tail 50" -ForegroundColor Gray
    }
    $allStepsSuccessful = $false
}

# ============================================================================
# STEP 6: Test Health Endpoint
# ============================================================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "STEP 6: Testing Health Endpoint" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

try {
    $health = curl -s http://localhost:8000/health | ConvertFrom-Json
    
    Write-Host "Server Status:" -ForegroundColor Cyan
    Write-Host "  Version: $($health.version)" -ForegroundColor Gray
    Write-Host "  Environment: $($health.environment)" -ForegroundColor Gray
    
    if ($health.services.qdrant.status -eq "connected") {
        Write-Host "✅ Qdrant: Connected" -ForegroundColor Green
    } else {
        Write-Host "❌ Qdrant: $($health.services.qdrant.status)" -ForegroundColor Red
        $allStepsSuccessful = $false
    }
    
    if ($health.services.embeddings.status -eq "loaded") {
        Write-Host "✅ Embeddings: Loaded ($($health.services.embeddings.model))" -ForegroundColor Green
    } else {
        Write-Host "❌ Embeddings: $($health.services.embeddings.status)" -ForegroundColor Red
        $allStepsSuccessful = $false
    }
    
} catch {
    Write-Host "❌ Failed to query health endpoint" -ForegroundColor Red
    Write-Host "   Error: $_" -ForegroundColor Gray
    $allStepsSuccessful = $false
}

# ============================================================================
# FINAL SUMMARY
# ============================================================================
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                    FINAL SUMMARY                           ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

if ($allStepsSuccessful) {
    Write-Host "🎉 SUCCESS! All systems operational" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "1. Restart Claude Code CLI" -ForegroundColor White
    Write-Host "2. Run: /mcp" -ForegroundColor White
    Write-Host "3. Verify Context server shows 'Connected ✅'" -ForegroundColor White
    Write-Host "4. Test search: 'Use Context MCP to search for FastMCP'" -ForegroundColor White
} else {
    Write-Host "⚠️  PARTIAL SUCCESS - Some issues remain" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Check logs: docker logs context-server --tail 100" -ForegroundColor White
    Write-Host "2. Verify model cache: ls $env:USERPROFILE\.cache\huggingface" -ForegroundColor White
    Write-Host "3. Review: COMPLETE_DIAGNOSIS_AND_SOLUTION.md" -ForegroundColor White
}

Write-Host ""
Write-Host "Documentation:" -ForegroundColor Cyan
Write-Host "  - COMPLETE_DIAGNOSIS_AND_SOLUTION.md" -ForegroundColor Gray
Write-Host "  - README_MCP_CONNECTION_FIX.md" -ForegroundColor Gray
Write-Host ""

