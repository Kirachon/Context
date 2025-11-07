#!/usr/bin/env pwsh
# Download Embedding Model for Context MCP Server
# This script downloads the sentence-transformers model on the host machine
# and configures Docker to use the cached model

Write-Host "=== Embedding Model Download Script ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if Python is installed
Write-Host "Step 1: Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.8+ first." -ForegroundColor Red
    Write-Host "   Download from: https://www.python.org/downloads/" -ForegroundColor Gray
    exit 1
}

# Step 2: Check if sentence-transformers is installed
Write-Host ""
Write-Host "Step 2: Checking sentence-transformers package..." -ForegroundColor Yellow
$stInstalled = python -c "import sentence_transformers; print('installed')" 2>&1

if ($stInstalled -notlike "*installed*") {
    Write-Host "⚠️  sentence-transformers not found. Installing..." -ForegroundColor Yellow
    Write-Host "   This may take 2-3 minutes..." -ForegroundColor Gray
    
    pip install sentence-transformers --quiet
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install sentence-transformers" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ sentence-transformers installed successfully" -ForegroundColor Green
} else {
    Write-Host "✅ sentence-transformers already installed" -ForegroundColor Green
}

# Step 3: Download the model
Write-Host ""
Write-Host "Step 3: Downloading embedding model (all-MiniLM-L6-v2)..." -ForegroundColor Yellow
Write-Host "   This may take 5-10 minutes depending on your internet speed..." -ForegroundColor Gray
Write-Host "   Model size: ~90 MB" -ForegroundColor Gray
Write-Host ""

$downloadScript = @"
from sentence_transformers import SentenceTransformer
import os

print('Downloading model...')
model = SentenceTransformer('all-MiniLM-L6-v2')
print('✅ Model downloaded successfully')

# Get cache location
cache_dir = os.path.expanduser('~/.cache/huggingface')
print(f'Model cached at: {cache_dir}')
"@

$downloadScript | python

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to download model" -ForegroundColor Red
    Write-Host "   This might be due to network issues or firewall blocking HuggingFace" -ForegroundColor Gray
    Write-Host "   Try:" -ForegroundColor Gray
    Write-Host "   1. Check your internet connection" -ForegroundColor Gray
    Write-Host "   2. Disable VPN/proxy temporarily" -ForegroundColor Gray
    Write-Host "   3. Check firewall settings" -ForegroundColor Gray
    exit 1
}

Write-Host "✅ Model downloaded successfully" -ForegroundColor Green

# Step 4: Find model location
Write-Host ""
Write-Host "Step 4: Locating model cache..." -ForegroundColor Yellow

$cacheDir = "$env:USERPROFILE\.cache\huggingface"
if (Test-Path $cacheDir) {
    Write-Host "✅ Model cache found at: $cacheDir" -ForegroundColor Green
    
    # List model files
    $modelFiles = Get-ChildItem -Path $cacheDir -Recurse -Filter "*all-MiniLM-L6-v2*" | Select-Object -First 5
    if ($modelFiles) {
        Write-Host "   Model files:" -ForegroundColor Gray
        $modelFiles | ForEach-Object { Write-Host "   - $($_.FullName)" -ForegroundColor Gray }
    }
} else {
    Write-Host "⚠️  Cache directory not found at expected location" -ForegroundColor Yellow
    Write-Host "   Checking alternative locations..." -ForegroundColor Gray
    
    $altCache = "$env:USERPROFILE\.cache\torch"
    if (Test-Path $altCache) {
        $cacheDir = $altCache
        Write-Host "✅ Found cache at: $cacheDir" -ForegroundColor Green
    }
}

# Step 5: Create models directory in project
Write-Host ""
Write-Host "Step 5: Setting up project model directory..." -ForegroundColor Yellow

$projectRoot = "D:\GitProjects\Context"
$modelsDir = "$projectRoot\models"

if (-not (Test-Path $modelsDir)) {
    New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null
    Write-Host "✅ Created models directory: $modelsDir" -ForegroundColor Green
} else {
    Write-Host "✅ Models directory already exists" -ForegroundColor Green
}

# Step 6: Copy model to project (optional - can also mount host cache)
Write-Host ""
Write-Host "Step 6: Model mounting strategy..." -ForegroundColor Yellow
Write-Host "   Option A: Mount host cache directory (recommended)" -ForegroundColor Cyan
Write-Host "   Option B: Copy model to project directory" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Using Option A (mount host cache) - no copy needed" -ForegroundColor Green

# Step 7: Update docker-compose.yml
Write-Host ""
Write-Host "Step 7: Checking docker-compose.yml configuration..." -ForegroundColor Yellow

$dockerComposePath = "$projectRoot\deployment\docker\docker-compose.yml"
$dockerComposeContent = Get-Content $dockerComposePath -Raw

if ($dockerComposeContent -like "*/.cache/huggingface*") {
    Write-Host "✅ docker-compose.yml already configured with model cache mount" -ForegroundColor Green
} else {
    Write-Host "⚠️  docker-compose.yml needs to be updated" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Add this to the context-server service volumes:" -ForegroundColor Cyan
    Write-Host "   volumes:" -ForegroundColor Gray
    Write-Host "     - $($cacheDir):/root/.cache/huggingface:ro" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   Would you like me to update it automatically? (Y/N)" -ForegroundColor Yellow
    # Note: In automated mode, we'll create a separate script for this
}

# Step 8: Summary
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "✅ Python installed and working" -ForegroundColor Green
Write-Host "✅ sentence-transformers package installed" -ForegroundColor Green
Write-Host "✅ Embedding model downloaded" -ForegroundColor Green
Write-Host "✅ Model cache located at: $cacheDir" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Update docker-compose.yml to mount model cache" -ForegroundColor White
Write-Host "2. Restart context-server container" -ForegroundColor White
Write-Host "3. Verify embedding service loads successfully" -ForegroundColor White
Write-Host ""
Write-Host "Commands to run:" -ForegroundColor Cyan
Write-Host "  docker-compose -f deployment/docker/docker-compose.yml restart context-server" -ForegroundColor Gray
Write-Host "  docker logs context-server --tail 50 | Select-String 'embedding'" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ Model download complete!" -ForegroundColor Green

