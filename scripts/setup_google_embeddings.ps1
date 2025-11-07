#!/usr/bin/env pwsh
# Setup Google Embeddings for Context MCP Server
# This script configures the system to use Google's Gemini API for embeddings

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Google Embeddings Setup - Context MCP Server            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$projectRoot = "D:\GitProjects\Context"
$envFile = "$projectRoot\deployment\docker\.env"

# Step 1: Get Google API Key
Write-Host "Step 1: Google API Key Configuration" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

Write-Host "Please enter your Google API key:" -ForegroundColor Cyan
Write-Host "(Get one at: https://makersuite.google.com/app/apikey)" -ForegroundColor Gray
$apiKey = Read-Host "Google API Key"

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host "❌ API key is required" -ForegroundColor Red
    exit 1
}

Write-Host "✅ API key received" -ForegroundColor Green

# Step 2: Update .env file
Write-Host ""
Write-Host "Step 2: Updating Environment Configuration" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

Write-Host "📁 Configuration file: $envFile" -ForegroundColor Cyan
Write-Host "   (This file is gitignored - your API key is safe)" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path $envFile)) {
    Write-Host "⚠️  .env file not found, creating from example..." -ForegroundColor Yellow
    Copy-Item "$projectRoot\.env.example" $envFile
    Write-Host "✅ Created .env file from template" -ForegroundColor Green
}

# Read current .env
$envContent = Get-Content $envFile -Raw

# Update or add Google API key
if ($envContent -match "GOOGLE_API_KEY=.*") {
    $envContent = $envContent -replace "GOOGLE_API_KEY=.*", "GOOGLE_API_KEY=$apiKey"
    Write-Host "✅ Updated existing GOOGLE_API_KEY" -ForegroundColor Green
} else {
    $envContent += "`nGOOGLE_API_KEY=$apiKey"
    Write-Host "✅ Added GOOGLE_API_KEY" -ForegroundColor Green
}

# Update embeddings provider
if ($envContent -match "EMBEDDINGS_PROVIDER=.*") {
    $envContent = $envContent -replace "EMBEDDINGS_PROVIDER=.*", "EMBEDDINGS_PROVIDER=google"
    Write-Host "✅ Updated EMBEDDINGS_PROVIDER to 'google'" -ForegroundColor Green
} else {
    $envContent += "`nEMBEDDINGS_PROVIDER=google"
    Write-Host "✅ Added EMBEDDINGS_PROVIDER=google" -ForegroundColor Green
}

# Update vector size for Google embeddings (768 dimensions)
if ($envContent -match "QDRANT_VECTOR_SIZE=.*") {
    $envContent = $envContent -replace "QDRANT_VECTOR_SIZE=.*", "QDRANT_VECTOR_SIZE=768"
    Write-Host "✅ Updated QDRANT_VECTOR_SIZE to 768 (Google embeddings)" -ForegroundColor Green
} else {
    $envContent += "`nQDRANT_VECTOR_SIZE=768"
    Write-Host "✅ Added QDRANT_VECTOR_SIZE=768" -ForegroundColor Green
}

# Save updated .env
Set-Content -Path $envFile -Value $envContent
Write-Host "✅ Configuration saved to: $envFile" -ForegroundColor Green

# Step 3: Recreate Qdrant collection with new vector size
Write-Host ""
Write-Host "Step 3: Recreating Qdrant Collection" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""
Write-Host "⚠️  The Qdrant collection needs to be recreated with 768 dimensions" -ForegroundColor Yellow
Write-Host "   This will DELETE existing indexed data" -ForegroundColor Red
Write-Host ""
$confirm = Read-Host "Recreate Qdrant collection? (Y/N)"

if ($confirm -eq "Y" -or $confirm -eq "y") {
    Write-Host "Deleting existing collection..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:6333/collections/context_vectors" -Method Delete -ErrorAction SilentlyContinue
        Write-Host "✅ Existing collection deleted" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Collection may not exist (this is OK)" -ForegroundColor Yellow
    }
    
    Write-Host "Creating new collection with 768 dimensions..." -ForegroundColor Cyan
    
    $body = @{
        vectors = @{
            size = 768
            distance = "Cosine"
        }
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:6333/collections/context_vectors" -Method Put -Body $body -ContentType "application/json"
        Write-Host "✅ New collection created successfully" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to create collection: $_" -ForegroundColor Red
        Write-Host "   The collection will be created automatically on first use" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠️  Skipped collection recreation" -ForegroundColor Yellow
    Write-Host "   You'll need to manually delete and recreate the collection" -ForegroundColor Gray
}

# Step 4: Restart container
Write-Host ""
Write-Host "Step 4: Restarting Context Server" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

docker-compose -f deployment/docker/docker-compose.yml restart context-server

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Container restarted successfully" -ForegroundColor Green
    Write-Host "   Waiting 20 seconds for initialization..." -ForegroundColor Gray
    Start-Sleep -Seconds 20
} else {
    Write-Host "❌ Failed to restart container" -ForegroundColor Red
    exit 1
}

# Step 5: Verify setup
Write-Host ""
Write-Host "Step 5: Verifying Setup" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

$logs = docker logs context-server --tail 50 2>&1

if ($logs -like "*Google embeddings initialized*") {
    Write-Host "✅ Google embeddings initialized successfully!" -ForegroundColor Green
} elseif ($logs -like "*GOOGLE_API_KEY*" -or $logs -like "*Google*") {
    Write-Host "⚠️  Google embeddings configuration detected, check logs:" -ForegroundColor Yellow
    Write-Host "   docker logs context-server --tail 50" -ForegroundColor Gray
} else {
    Write-Host "⚠️  Could not verify Google embeddings initialization" -ForegroundColor Yellow
    Write-Host "   Check logs: docker logs context-server --tail 50" -ForegroundColor Gray
}

# Final summary
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                    SETUP COMPLETE                          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Google embeddings configured successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Provider: Google (Gemini API)" -ForegroundColor Gray
Write-Host "  Model: text-embedding-004" -ForegroundColor Gray
Write-Host "  Dimensions: 768" -ForegroundColor Gray
Write-Host "  API Key: $($apiKey.Substring(0, 10))..." -ForegroundColor Gray
Write-Host ""
Write-Host "Benefits:" -ForegroundColor Yellow
Write-Host "  ✅ No local model download required" -ForegroundColor Green
Write-Host "  ✅ No SSL/network issues" -ForegroundColor Green
Write-Host "  ✅ High-quality embeddings from Google" -ForegroundColor Green
Write-Host "  ✅ Reduced memory usage in container" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Restart Claude Code CLI" -ForegroundColor White
Write-Host "2. Run: /mcp" -ForegroundColor White
Write-Host "3. Verify Context server shows 'Connected ✅'" -ForegroundColor White
Write-Host "4. Test search functionality" -ForegroundColor White
Write-Host ""

