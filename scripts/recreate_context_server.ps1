#!/usr/bin/env pwsh
# Recreate Context Server Container with New Volume Mounts
# This script stops and recreates the container to pick up the new HuggingFace cache mount

Write-Host "=== Recreating Context Server Container ===" -ForegroundColor Cyan
Write-Host ""

$projectRoot = "D:\GitProjects\Context"
Set-Location $projectRoot

# Step 1: Stop and remove the container
Write-Host "Step 1: Stopping and removing existing container..." -ForegroundColor Yellow
docker-compose -f deployment/docker/docker-compose.yml stop context-server
docker-compose -f deployment/docker/docker-compose.yml rm -f context-server

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to remove container" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Container removed" -ForegroundColor Green

# Step 2: Recreate the container with new configuration
Write-Host ""
Write-Host "Step 2: Recreating container with new volume mounts..." -ForegroundColor Yellow
docker-compose -f deployment/docker/docker-compose.yml up -d context-server

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to recreate container" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Container recreated successfully" -ForegroundColor Green

# Step 3: Wait for initialization
Write-Host ""
Write-Host "Step 3: Waiting for container to initialize (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Step 4: Verify volume mounts
Write-Host ""
Write-Host "Step 4: Verifying volume mounts..." -ForegroundColor Yellow
$mounts = docker inspect context-server --format '{{json .Mounts}}' | ConvertFrom-Json

$huggingfaceMount = $mounts | Where-Object { $_.Destination -eq "/root/.cache/huggingface" }

if ($huggingfaceMount) {
    Write-Host "✅ HuggingFace cache mount verified:" -ForegroundColor Green
    Write-Host "   Source: $($huggingfaceMount.Source)" -ForegroundColor Gray
    Write-Host "   Destination: $($huggingfaceMount.Destination)" -ForegroundColor Gray
    Write-Host "   Read-Only: $(-not $huggingfaceMount.RW)" -ForegroundColor Gray
} else {
    Write-Host "❌ HuggingFace cache mount NOT found!" -ForegroundColor Red
    Write-Host "   This means the docker-compose.yml change didn't take effect" -ForegroundColor Gray
    exit 1
}

# Step 5: Check logs for model loading
Write-Host ""
Write-Host "Step 5: Checking logs for model loading..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

$logs = docker logs context-server --tail 50 2>&1

if ($logs -like "*Embedding service initialized*" -or $logs -like "*EmbeddingService initialized*") {
    Write-Host "✅ Embedding model loaded successfully!" -ForegroundColor Green
} elseif ($logs -like "*SSL*" -or $logs -like "*SSLError*") {
    Write-Host "⚠️  Still seeing SSL errors - model may not be cached on host" -ForegroundColor Yellow
    Write-Host "   You need to download the model on your host machine first" -ForegroundColor Gray
    Write-Host "   Run: .\scripts\download_embedding_model.ps1" -ForegroundColor Cyan
} else {
    Write-Host "⏳ Model still loading... check logs:" -ForegroundColor Yellow
    Write-Host "   docker logs context-server -f" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "✅ Container recreated with new volume mounts" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. If you see SSL errors, download the model on host:" -ForegroundColor White
Write-Host "   .\scripts\download_embedding_model.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Then recreate the container again:" -ForegroundColor White
Write-Host "   .\scripts\recreate_context_server.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Verify health:" -ForegroundColor White
Write-Host "   curl http://localhost:8000/health | ConvertFrom-Json" -ForegroundColor Gray
Write-Host ""

